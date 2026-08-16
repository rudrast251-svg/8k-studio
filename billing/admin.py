from django.contrib import admin

from .models import CreditTransaction, Plan


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'price_usd', 'monthly_credits', 'max_resolution', 'is_featured', 'is_active', 'order']
    list_editable = ['order', 'is_active', 'is_featured']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(CreditTransaction)
class CreditTransactionAdmin(admin.ModelAdmin):
    list_display = ['user', 'amount', 'balance_after', 'reason', 'job', 'created_at']
    list_filter = ['reason', 'created_at']
    search_fields = ['user__email', 'note']
    readonly_fields = [f.name for f in CreditTransaction._meta.fields]
    date_hierarchy = 'created_at'

    def has_add_permission(self, request):
        return False
