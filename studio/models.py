import os
import uuid

from django.conf import settings
from django.db import models
from django.urls import reverse


def asset_upload_path(instance, filename):
    ext = os.path.splitext(filename)[1].lower()
    owner_id = instance.owner_id or 'demo'
    return f'assets/{owner_id}/{uuid.uuid4().hex}{ext}'


class Asset(models.Model):
    class Kind(models.TextChoices):
        IMAGE = 'image', 'Image'
        VIDEO = 'video', 'Video'

    class Source(models.TextChoices):
        UPLOAD = 'upload', 'User upload'
        ENHANCED = 'enhanced', 'AI enhanced output'
        DEMO_SAMPLE = 'demo_sample', 'Demo sample library'

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.CASCADE, related_name='assets'
    )
    file = models.FileField(upload_to=asset_upload_path, max_length=500)
    kind = models.CharField(max_length=10, choices=Kind.choices)
    source = models.CharField(max_length=15, choices=Source.choices, default=Source.UPLOAD)
    original_name = models.CharField(max_length=255, blank=True)
    file_size = models.PositiveBigIntegerField(default=0)
    width = models.PositiveIntegerField(null=True, blank=True)
    height = models.PositiveIntegerField(null=True, blank=True)
    duration_seconds = models.FloatField(null=True, blank=True)
    is_public_demo = models.BooleanField(default=False)
    label = models.CharField(max_length=140, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.label or self.original_name or self.file.name

    @property
    def resolution_label(self):
        if self.width and self.height:
            return f'{self.width}x{self.height}'
        return '—'

    @property
    def file_size_mb(self):
        return round(self.file_size / (1024 * 1024), 2)


class Job(models.Model):
    class JobType(models.TextChoices):
        IMAGE_ENHANCE = 'image_enhance', 'Image enhancement'
        VIDEO_ENHANCE = 'video_enhance', 'Video enhancement'

    class Status(models.TextChoices):
        UPLOADED = 'uploaded', 'Uploaded'
        PROCESSING = 'processing', 'Processing'
        COMPLETED = 'completed', 'Completed'
        FAILED = 'failed', 'Failed'

    class Provider(models.TextChoices):
        DEMO = 'demo', 'Demo (local processing)'
        REPLICATE = 'replicate', 'Replicate GPU API'

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='jobs')
    job_type = models.CharField(max_length=20, choices=JobType.choices)
    input_asset = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name='jobs_as_input')
    output_asset = models.ForeignKey(
        Asset, null=True, blank=True, on_delete=models.SET_NULL, related_name='jobs_as_output'
    )
    instruction = models.TextField(help_text="The user's plain-English instruction.")
    parsed_ops = models.JSONField(default=dict, blank=True)
    skipped_ops = models.JSONField(default=list, blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.UPLOADED)
    progress_percent = models.PositiveSmallIntegerField(default=0)
    provider = models.CharField(max_length=10, choices=Provider.choices, default=Provider.DEMO)
    provider_job_id = models.CharField(max_length=200, blank=True)
    credits_cost = models.PositiveIntegerField(default=1)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Job #{self.id} ({self.get_status_display()})'

    def get_absolute_url(self):
        return reverse('studio:job_detail', args=[self.pk])

    @property
    def is_terminal(self):
        return self.status in (self.Status.COMPLETED, self.Status.FAILED)


class Notification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    job = models.ForeignKey(Job, null=True, blank=True, on_delete=models.CASCADE, related_name='notifications')
    message = models.CharField(max_length=255)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.message
