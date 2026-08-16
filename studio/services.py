import logging

import cv2
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone
from PIL import Image

from billing.services import InsufficientCreditsError, charge_for_job, refund_for_job
from .ai import image_pipeline, video_pipeline
from .ai.instructions import parse_instruction
from .models import Asset, Job, Notification

logger = logging.getLogger(__name__)

IMAGE_BASE_COST = {'4K': 1, '8K': 2}
VIDEO_BASE_COST = {'4K': 5, '8K': 10}


def probe_asset(asset: Asset):
    """Fill in width/height/duration metadata for a freshly-uploaded asset."""
    try:
        if asset.kind == Asset.Kind.IMAGE:
            asset.file.open('rb')
            with Image.open(asset.file) as img:
                asset.width, asset.height = img.width, img.height
            asset.file.close()
        else:
            asset.file.open('rb')
            data = asset.file.read()
            asset.file.close()
            import tempfile
            from pathlib import Path
            with tempfile.TemporaryDirectory() as tmp:
                p = Path(tmp) / 'probe.mp4'
                p.write_bytes(data)
                cap = cv2.VideoCapture(str(p))
                if cap.isOpened():
                    asset.width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or None
                    asset.height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or None
                    fps = cap.get(cv2.CAP_PROP_FPS) or 0
                    frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0
                    asset.duration_seconds = round(frame_count / fps, 2) if fps else None
                cap.release()
        asset.save(update_fields=['width', 'height', 'duration_seconds'])
    except Exception:
        logger.exception('Failed to probe metadata for asset %s', asset.pk)


def estimate_credits_cost(job_type: str, ops: dict) -> int:
    table = IMAGE_BASE_COST if job_type == Job.JobType.IMAGE_ENHANCE else VIDEO_BASE_COST
    target = ops.get('target_resolution', '4K') if ops.get('upscale') else '4K'
    cost = table.get(target, table['4K'])
    extra_ops = sum(1 for k in ('stabilize', 'interpolate_frames', 'face_restore', 'remove_background') if ops.get(k))
    return cost + extra_ops


@transaction.atomic
def create_job(user, asset: Asset, instruction: str) -> Job:
    job_type = Job.JobType.IMAGE_ENHANCE if asset.kind == Asset.Kind.IMAGE else Job.JobType.VIDEO_ENHANCE
    media_kind = 'image' if asset.kind == Asset.Kind.IMAGE else 'video'
    ops = parse_instruction(instruction, media_kind)
    cost = estimate_credits_cost(job_type, ops)

    job = Job.objects.create(
        owner=user,
        job_type=job_type,
        input_asset=asset,
        instruction=instruction,
        parsed_ops=ops,
        status=Job.Status.UPLOADED,
        credits_cost=cost,
    )
    try:
        charge_for_job(user, job)
    except InsufficientCreditsError:
        job.delete()
        raise
    return job


def process_job(job: Job):
    """Run the enhancement pipeline for a job. Called by the background worker."""
    job.status = Job.Status.PROCESSING
    job.started_at = timezone.now()
    job.progress_percent = 10
    job.save(update_fields=['status', 'started_at', 'progress_percent'])

    try:
        pipeline = image_pipeline if job.job_type == Job.JobType.IMAGE_ENHANCE else video_pipeline
        job.progress_percent = 35
        job.save(update_fields=['progress_percent'])

        result, provider = pipeline.run(job.input_asset, job.parsed_ops)
        if job.job_type == Job.JobType.IMAGE_ENHANCE:
            data, content_type, applied, skipped = result
            meta = {}
        else:
            data, content_type, applied, skipped, meta = result

        job.progress_percent = 80
        job.save(update_fields=['progress_percent'])

        ext = '.png' if content_type == 'image/png' else ('.jpg' if content_type == 'image/jpeg' else '.mp4')
        output_asset = Asset(
            owner=job.owner,
            kind=job.input_asset.kind,
            source=Asset.Source.ENHANCED,
            original_name=f'enhanced_{job.input_asset.original_name or job.input_asset.file.name}',
            file_size=len(data),
            width=meta.get('width') or job.input_asset.width,
            height=meta.get('height') or job.input_asset.height,
            duration_seconds=job.input_asset.duration_seconds,
            label=f'Enhanced output for job #{job.id}',
        )
        output_asset.file.save(f'job_{job.id}{ext}', ContentFile(data), save=False)
        output_asset.save()
        if not meta.get('width'):
            probe_asset(output_asset)

        job.output_asset = output_asset
        job.provider = Job.Provider.REPLICATE if provider == 'replicate' else Job.Provider.DEMO
        job.skipped_ops = skipped
        job.status = Job.Status.COMPLETED
        job.progress_percent = 100
        job.completed_at = timezone.now()
        job.save()

        Notification.objects.create(
            user=job.owner, job=job,
            message=f'Your {job.get_job_type_display().lower()} job #{job.id} is complete and ready to download.',
        )
    except Exception as exc:
        logger.exception('Job %s failed', job.pk)
        job.status = Job.Status.FAILED
        job.error_message = str(exc)[:2000]
        job.completed_at = timezone.now()
        job.save()
        try:
            refund_for_job(job.owner, job)
        except Exception:
            logger.exception('Failed to refund credits for job %s', job.pk)
        Notification.objects.create(
            user=job.owner, job=job,
            message=f'Job #{job.id} failed: {job.error_message[:120]}. Your credits were refunded.',
        )
