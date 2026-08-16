from django.contrib import admin
from django.utils.html import format_html

from .models import Asset, Job, Notification


@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = ['id', 'owner', 'kind', 'source', 'resolution_label', 'file_size_mb', 'is_public_demo', 'created_at']
    list_filter = ['kind', 'source', 'is_public_demo']
    search_fields = ['owner__email', 'original_name', 'label']
    readonly_fields = ['file_size', 'width', 'height', 'duration_seconds', 'created_at', 'preview']

    def preview(self, obj):
        if not obj.file:
            return '—'
        if obj.kind == Asset.Kind.IMAGE:
            return format_html('<img src="{}" style="max-width:320px;border-radius:8px" />', obj.file.url)
        return format_html('<video src="{}" style="max-width:320px;border-radius:8px" controls></video>', obj.file.url)


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ['id', 'owner', 'job_type', 'status', 'progress_percent', 'provider', 'credits_cost', 'created_at']
    list_filter = ['status', 'job_type', 'provider']
    search_fields = ['owner__email', 'instruction']
    readonly_fields = ['created_at', 'started_at', 'completed_at']
    date_hierarchy = 'created_at'
    actions = ['requeue_failed']

    @admin.action(description='Requeue selected failed jobs')
    def requeue_failed(self, request, queryset):
        updated = queryset.filter(status=Job.Status.FAILED).update(status=Job.Status.UPLOADED, progress_percent=0, error_message='')
        self.message_user(request, f'{updated} job(s) requeued.')


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'message', 'is_read', 'created_at']
    list_filter = ['is_read']
