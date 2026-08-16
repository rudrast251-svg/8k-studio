from django.contrib import admin

from .models import EditCommand, SiteConfig


@admin.register(SiteConfig)
class SiteConfigAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'primary_color', 'accent_color', 'background_color', 'updated_at']

    def has_add_permission(self, request):
        return not SiteConfig.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(EditCommand)
class EditCommandAdmin(admin.ModelAdmin):
    list_display = ['user', 'instruction', 'success', 'created_at']
    list_filter = ['success']
    readonly_fields = [f.name for f in EditCommand._meta.fields]

    def has_add_permission(self, request):
        return False
