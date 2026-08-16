from django.conf import settings
from django.db import models


class SiteConfig(models.Model):
    """Singleton row describing the editable public landing page."""

    headline = models.CharField(max_length=160, default='Turn any photo or video into 8K, cinematic quality.')
    subheadline = models.CharField(
        max_length=280,
        default='Upload your media, describe what you want in plain English, and let real AI upscaling do the rest.',
    )
    primary_color = models.CharField(max_length=7, default='#8b5cf6')
    accent_color = models.CharField(max_length=7, default='#3b82f6')
    background_color = models.CharField(max_length=7, default='#05050a')
    hero_video = models.ForeignKey(
        'studio.Asset', null=True, blank=True, on_delete=models.SET_NULL, related_name='+',
    )
    hero_image = models.ForeignKey(
        'studio.Asset', null=True, blank=True, on_delete=models.SET_NULL, related_name='+',
    )
    hero_autoplay = models.BooleanField(default=True)
    hero_muted = models.BooleanField(default=True)
    hero_loop = models.BooleanField(default=True)
    cta_label = models.CharField(max_length=40, default='Upload & Enhance Free')
    cta_url = models.CharField(max_length=200, default='/accounts/sign-up/')
    features = models.JSONField(default=list, blank=True)
    faqs = models.JSONField(default=list, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='+',
    )

    class Meta:
        verbose_name = 'Site configuration'
        verbose_name_plural = 'Site configuration'

    def __str__(self):
        return 'Public site configuration'

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class EditCommand(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='site_edit_commands')
    instruction = models.TextField()
    patch_applied = models.JSONField(default=dict, blank=True)
    success = models.BooleanField(default=True)
    error_message = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user}: {self.instruction[:40]}'
