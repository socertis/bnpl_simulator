from django.contrib import admin
from .models import PaymentPlan, Installment

class InstallmentInline(admin.TabularInline):
    model = Installment
    extra = 0
    readonly_fields = ['installment_number', 'created_at', 'updated_at']

@admin.register(PaymentPlan)
class PaymentPlanAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'user_email', 'merchant', 'total_amount', 
        'number_of_installments', 'status', 'created_at'
    ]
    list_filter = ['status', 'created_at', 'start_date']
    search_fields = ['user_email', 'merchant__email']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [InstallmentInline]
    
    fieldsets = (
        ('Plan Information', {
            'fields': ('merchant', 'user_email', 'total_amount', 'number_of_installments')
        }),
        ('Dates', {
            'fields': ('start_date', 'status')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(Installment)
class InstallmentAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'payment_plan', 'installment_number', 
        'amount', 'due_date', 'status', 'paid_date'
    ]
    list_filter = ['status', 'due_date', 'paid_date']
    search_fields = ['payment_plan__user_email']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Installment Information', {
            'fields': ('payment_plan', 'installment_number', 'amount', 'due_date')
        }),
        ('Status', {
            'fields': ('status', 'paid_date')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )