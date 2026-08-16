from django.contrib import admin

from .models import CreditTransaction, PaymentRequest, Plan
from .services import approve_payment_request, reject_payment_request


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'price_inr', 'monthly_credits', 'max_resolution', 'is_featured', 'is_active', 'order']
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


@admin.register(PaymentRequest)
class PaymentRequestAdmin(admin.ModelAdmin):
    list_display = ['user', 'plan', 'amount_inr', 'upi_ref', 'status', 'created_at', 'reviewed_by']
    list_filter = ['status', 'plan']
    search_fields = ['user__email', 'upi_ref']
    readonly_fields = ['user', 'plan', 'amount_inr', 'upi_ref', 'created_at', 'reviewed_by', 'reviewed_at']
    date_hierarchy = 'created_at'
    actions = ['approve_payments', 'reject_payments']

    def has_add_permission(self, request):
        return False

    @admin.action(description='✅ Approve selected payments (grants plan + credits)')
    def approve_payments(self, request, queryset):
        count = 0
        for pr in queryset.filter(status=PaymentRequest.Status.PENDING):
            approve_payment_request(pr, request.user)
            count += 1
        self.message_user(request, f'{count} payment(s) approved and credited.')

    @admin.action(description='❌ Reject selected payments')
    def reject_payments(self, request, queryset):
        count = 0
        for pr in queryset.filter(status=PaymentRequest.Status.PENDING):
            reject_payment_request(pr, request.user)
            count += 1
        self.message_user(request, f'{count} payment(s) rejected.')
