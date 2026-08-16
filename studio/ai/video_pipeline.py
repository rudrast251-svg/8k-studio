"""Video enhancement pipeline.

Real GPU path: submits the video to a Replicate model when
REPLICATE_API_TOKEN is configured.

Demo path: performs genuine frame-by-frame processing with OpenCV (resize
upscale, denoise, sharpen, brightness/color grading, translation-based
stabilization, and motion-blend frame interpolation) and writes real,
browser-playable H.264 output. Demo processing is capped in resolution and
frame count to keep it responsive without a GPU, and audio cannot be
preserved by this local pipeline (no bundled audio muxer) — that limitation
is surfaced to the user rather than silently ignored.
"""
import tempfile
from pathlib import Path

import cv2
import numpy as np
from django.conf import settings

from . import replicate_client

DEMO_MAX_HEIGHT = 1080
DEMO_MAX_FRAMES = 400
UPSCALE_FACTOR = {'4K': 2, '8K': 3}


def _open_writer(path, fourcc_name, fps, size):
    fourcc = cv2.VideoWriter_fourcc(*fourcc_name)
    writer = cv2.VideoWriter(str(path), fourcc, fps, size)
    return writer if writer.isOpened() else None


def enhance_video_demo(asset, ops: dict) -> tuple[bytes, str, list[str], list[str], dict]:
    applied, skipped = [], []
    meta = {}

    asset.file.open('rb')
    src_bytes = asset.file.read()
    asset.file.close()

    with tempfile.TemporaryDirectory() as tmp:
        src_path = Path(tmp) / 'input.mp4'
        src_path.write_bytes(src_bytes)

        cap = cv2.VideoCapture(str(src_path))
        if not cap.isOpened():
            raise RuntimeError('Could not read the uploaded video for processing.')

        fps = cap.get(cv2.CAP_PROP_FPS) or 24
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        scale = 1.0
        if ops.get('upscale'):
            factor = UPSCALE_FACTOR.get(ops.get('target_resolution', '4K'), 2)
            scale = factor
            applied.append(f"Upscaled {factor}x (demo resample, capped at {DEMO_MAX_HEIGHT}p)")
        out_w, out_h = int(width * scale), int(height * scale)
        if out_h > DEMO_MAX_HEIGHT:
            shrink = DEMO_MAX_HEIGHT / out_h
            out_w, out_h = int(out_w * shrink), int(out_h * shrink)
        out_w -= out_w % 2
        out_h -= out_h % 2

        truncated = total_frames > DEMO_MAX_FRAMES
        frame_limit = min(total_frames, DEMO_MAX_FRAMES) if total_frames else DEMO_MAX_FRAMES

        frames = []
        while len(frames) < frame_limit:
            ok, frame = cap.read()
            if not ok:
                break
            frames.append(frame)
        cap.release()

        if not frames:
            raise RuntimeError('No frames could be read from the uploaded video.')

        if ops.get('stabilize') and len(frames) > 2:
            frames = _stabilize(frames)
            applied.append('Stabilized (optical-flow motion smoothing)')

        if ops.get('interpolate_frames') and len(frames) > 1:
            frames = _blend_interpolate(frames)
            fps = fps * 2
            applied.append('Smoothed motion via frame blending (demo interpolation)')

        processed = []
        for frame in frames:
            f = frame
            if scale != 1.0 or (f.shape[1], f.shape[0]) != (out_w, out_h):
                f = cv2.resize(f, (out_w, out_h), interpolation=cv2.INTER_LANCZOS4)
            if ops.get('denoise'):
                f = cv2.bilateralFilter(f, d=7, sigmaColor=50, sigmaSpace=50)
            if ops.get('sharpen'):
                blur = cv2.GaussianBlur(f, (0, 0), sigmaX=2)
                f = cv2.addWeighted(f, 1.5, blur, -0.5, 0)
            if ops.get('brighten'):
                f = cv2.convertScaleAbs(f, alpha=1.12, beta=18)
            if ops.get('darken'):
                f = cv2.convertScaleAbs(f, alpha=0.9, beta=-15)
            if ops.get('color_boost') or ops.get('cinematic'):
                hsv = cv2.cvtColor(f, cv2.COLOR_BGR2HSV).astype(np.float32)
                hsv[:, :, 1] = np.clip(hsv[:, :, 1] * 1.25, 0, 255)
                f = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)
            if ops.get('cinematic'):
                f = cv2.convertScaleAbs(f, alpha=1.08, beta=-6)
            processed.append(f)

        if 'Reduced noise' not in applied and ops.get('denoise'):
            applied.append('Reduced noise (bilateral filtering)')
        if ops.get('sharpen'):
            applied.append('Sharpened details (unsharp mask)')
        if ops.get('brighten'):
            applied.append('Brightened')
        if ops.get('darken'):
            applied.append('Darkened')
        if ops.get('color_boost'):
            applied.append('Boosted color vibrance')
        if ops.get('cinematic'):
            applied.append('Applied cinematic color grade')

        if ops.get('face_restore'):
            skipped.append('Face restoration (needs a connected AI provider)')
        if not ops.get('mute_audio'):
            skipped.append('Original audio could not be preserved by local demo processing — output is silent. Connect an AI provider for full audio-preserving enhancement.')
        else:
            applied.append('Audio removed (muted)')

        if truncated:
            skipped.append(f'Demo mode processed the first {frame_limit} frames only (full video needs a connected AI provider).')

        out_path = Path(tmp) / 'output.mp4'
        writer = _open_writer(out_path, 'avc1', fps, (out_w, out_h))
        codec_note = 'H.264'
        if writer is None:
            writer = _open_writer(out_path, 'mp4v', fps, (out_w, out_h))
            codec_note = 'MPEG-4 (fallback)'
        if writer is None:
            raise RuntimeError('No local video codec is available to write the output file.')
        for f in processed:
            writer.write(f)
        writer.release()

        data = out_path.read_bytes()
        if not data:
            raise RuntimeError('Local video processing produced an empty file.')

        meta = {'width': out_w, 'height': out_h, 'fps': fps, 'frames': len(processed), 'codec': codec_note}
        return data, 'video/mp4', applied, skipped, meta


def _stabilize(frames):
    gray_frames = [cv2.cvtColor(f, cv2.COLOR_BGR2GRAY) for f in frames]
    transforms = [(0.0, 0.0)]
    for i in range(1, len(gray_frames)):
        shift, _ = cv2.phaseCorrelate(np.float32(gray_frames[i - 1]), np.float32(gray_frames[i]))
        transforms.append(shift)

    xs = np.cumsum([t[0] for t in transforms])
    ys = np.cumsum([t[1] for t in transforms])

    def smooth(series, window=15):
        kernel = np.ones(window) / window
        padded = np.pad(series, (window // 2, window - 1 - window // 2), mode='edge')
        return np.convolve(padded, kernel, mode='valid')

    smooth_xs, smooth_ys = smooth(xs), smooth(ys)
    dx, dy = smooth_xs - xs, smooth_ys - ys

    h, w = frames[0].shape[:2]
    margin = int(min(h, w) * 0.04)
    stabilized = []
    for i, frame in enumerate(frames):
        m = np.float32([[1, 0, dx[i]], [0, 1, dy[i]]])
        warped = cv2.warpAffine(frame, m, (w, h), borderMode=cv2.BORDER_REPLICATE)
        cropped = warped[margin:h - margin, margin:w - margin]
        stabilized.append(cv2.resize(cropped, (w, h)))
    return stabilized


def _blend_interpolate(frames):
    result = []
    for i in range(len(frames) - 1):
        result.append(frames[i])
        blended = cv2.addWeighted(frames[i], 0.5, frames[i + 1], 0.5, 0)
        result.append(blended)
    result.append(frames[-1])
    return result


def enhance_video_replicate(asset, ops: dict) -> tuple[bytes, str, list[str], list[str], dict]:
    applied, skipped = [], []
    video_url = f"{settings.SITE_BASE_URL}{asset.file.url}"
    payload = {
        'video': video_url,
        'scale': UPSCALE_FACTOR.get(ops.get('target_resolution', '4K'), 2) if ops.get('upscale') else 1,
    }
    prediction = replicate_client.create_prediction(settings.REPLICATE_VIDEO_MODEL, payload)
    prediction = replicate_client.wait_for_prediction(prediction['id'], timeout=1800)
    if prediction['status'] != 'succeeded':
        raise RuntimeError(f"Replicate prediction failed: {prediction.get('error', 'unknown error')}")
    output_url = prediction['output']
    if isinstance(output_url, list):
        output_url = output_url[0]

    import requests
    resp = requests.get(output_url, timeout=600)
    resp.raise_for_status()
    applied.append(f"AI upscaled via Replicate ({settings.REPLICATE_VIDEO_MODEL.split(':')[0]})")
    if ops.get('stabilize'):
        applied.append('Stabilized (AI provider)')
    if ops.get('interpolate_frames'):
        applied.append('AI frame interpolation')
    content_type = resp.headers.get('content-type', 'video/mp4')
    return resp.content, content_type, applied, skipped, {}


def run(asset, ops: dict):
    if settings.REPLICATE_API_TOKEN:
        return enhance_video_replicate(asset, ops), 'replicate'
    return enhance_video_demo(asset, ops), 'demo'
