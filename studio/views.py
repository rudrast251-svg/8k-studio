import os

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import FileResponse, Http404, HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from billing.services import InsufficientCreditsError
from .ai.instructions import humanize_ops
from .forms import UploadJobForm
from .models import Asset, Job, Notification
from .services import PlanRestrictionError, create_job, probe_asset, process_job
from .validation import UploadValidationError, validate_upload


@login_required
def dashboard(request):
    recent_jobs = Job.objects.filter(owner=request.user)[:6]
    stats = {
        'total_jobs': Job.objects.filter(owner=request.user).count(),
        'completed_jobs': Job.objects.filter(owner=request.user, status=Job.Status.COMPLETED).count(),
        'processing_jobs': Job.objects.filter(owner=request.user, status__in=[Job.Status.UPLOADED, Job.Status.PROCESSING]).count(),
        'asset_count': Asset.objects.filter(owner=request.user).count(),
    }
    return render(request, 'studio/dashboard.html', {
        'recent_jobs': recent_jobs,
        'stats': stats,
    })


@login_required
def upload(request):
    if request.method == 'POST':
        form = UploadJobForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                uploaded_file = form.cleaned_data.get('file')
                library_asset_id = form.cleaned_data.get('library_asset_id')
                if uploaded_file:
                    kind = validate_upload(uploaded_file)
                    asset = Asset.objects.create(
                        owner=request.user,
                        file=uploaded_file,
                        kind=kind,
                        source=Asset.Source.UPLOAD,
                        original_name=uploaded_file.name,
                        file_size=uploaded_file.size,
                    )
                    probe_asset(asset)
                else:
                    asset = get_object_or_404(Asset, pk=library_asset_id)
                    if asset.owner_id not in (request.user.id, None):
                        return HttpResponseForbidden('You do not have access to this asset.')

                job = create_job(request.user, asset, form.cleaned_data['instruction'])
                if settings.PROCESS_JOBS_INLINE:
                    process_job(job)
                    messages.success(request, f'Job #{job.id} processed.')
                else:
                    messages.success(request, f'Job #{job.id} queued for processing.')
                return redirect('studio:job_detail', pk=job.pk)
            except (UploadValidationError, ValidationError) as exc:
                messages.error(request, str(exc.message) if hasattr(exc, 'message') else str(exc))
            except PlanRestrictionError as exc:
                messages.error(request, str(exc))
                return redirect('billing:pricing')
            except InsufficientCreditsError as exc:
                messages.error(request, str(exc))
                return redirect('billing:pricing')
    else:
        form = UploadJobForm()

    library_assets = Asset.objects.filter(owner=request.user).exclude(source=Asset.Source.ENHANCED)[:12]
    demo_assets = Asset.objects.filter(is_public_demo=True)[:6]
    return render(request, 'studio/upload.html', {
        'form': form,
        'library_assets': library_assets,
        'demo_assets': demo_assets,
    })


@login_required
def job_list(request):
    status = request.GET.get('status', '')
    jobs = Job.objects.filter(owner=request.user)
    if status:
        jobs = jobs.filter(status=status)
    return render(request, 'studio/job_list.html', {'jobs': jobs, 'status_filter': status, 'statuses': Job.Status.choices})


@login_required
def job_detail(request, pk):
    job = get_object_or_404(Job, pk=pk, owner=request.user)
    return render(request, 'studio/job_detail.html', {
        'job': job,
        'applied_ops': humanize_ops(job.parsed_ops),
    })


@login_required
def job_status(request, pk):
    job = get_object_or_404(Job, pk=pk, owner=request.user)
    return JsonResponse({
        'status': job.status,
        'progress_percent': job.progress_percent,
        'error_message': job.error_message,
        'output_url': job.output_asset.file.url if job.output_asset else None,
    })


@login_required
def job_download(request, pk):
    job = get_object_or_404(Job, pk=pk, owner=request.user)
    if not job.output_asset:
        raise Http404('No completed output available for this job yet.')
    asset = job.output_asset
    asset.file.open('rb')
    ext = os.path.splitext(asset.file.name)[1]
    return FileResponse(asset.file, as_attachment=True, filename=f'8kstudio_{job.pk}{ext}')


@login_required
def library(request):
    assets = Asset.objects.filter(owner=request.user)
    kind = request.GET.get('kind', '')
    if kind:
        assets = assets.filter(kind=kind)
    return render(request, 'studio/library.html', {'assets': assets, 'kind_filter': kind})


@require_POST
@login_required
def notifications_mark_read(request):
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return JsonResponse({'ok': True})


@login_required
def notifications_list(request):
    notifications = Notification.objects.filter(user=request.user)[:20]
    return JsonResponse({
        'unread_count': Notification.objects.filter(user=request.user, is_read=False).count(),
        'notifications': [
            {'id': n.id, 'message': n.message, 'is_read': n.is_read, 'created_at': n.created_at.isoformat(), 'job_id': n.job_id}
            for n in notifications
        ],
    })
