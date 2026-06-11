# -*- coding: utf-8 -*-
from django.contrib import admin
from django.utils.html import format_html

from .models import Subscription


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        'store_name', 'owner_name', 'phone', 'plan',
        'price', 'colored_status', 'transaction_id', 'created_at',
    )
    list_filter = ('status', 'plan', 'country', 'payment_method', 'created_at')
    search_fields = ('store_name', 'owner_name', 'phone', 'transaction_id', 'license_key')
    readonly_fields = ('created_at', 'approved_at', 'license_key', 'expires_at', 'receipt_preview')
    actions = ['approve_subscriptions', 'reject_subscriptions']

    fieldsets = (
        ('معلومات المحل', {
            'fields': ('store_name', 'owner_name', 'phone', 'email', 'country'),
        }),
        ('الاشتراك', {
            'fields': ('plan', 'price', 'status'),
        }),
        ('الدفع', {
            'fields': ('payment_method', 'transaction_id', 'receipt_image', 'receipt_preview'),
        }),
        ('التفعيل', {
            'fields': ('license_key', 'expires_at', 'approved_at', 'admin_note'),
        }),
        ('النظام', {'fields': ('created_at',)}),
    )

    @admin.display(description='الحالة')
    def colored_status(self, obj):
        colors = {
            'pending': '#999', 'submitted': '#e69500',
            'approved': '#1a9e1a', 'rejected': '#cc2b2b',
        }
        return format_html(
            '<b style="color:{}">{}</b>',
            colors.get(obj.status, '#000'), obj.get_status_display(),
        )

    @admin.display(description='معاينة الإيصال')
    def receipt_preview(self, obj):
        if obj.receipt_image:
            return format_html(
                '<a href="{0}" target="_blank"><img src="{0}" style="max-width:320px;border:1px solid #ccc;border-radius:8px"></a>',
                obj.receipt_image.url,
            )
        return 'لا يوجد إيصال مرفوع'

    @admin.action(description='✅ موافقة وتوليد كود التفعيل')
    def approve_subscriptions(self, request, queryset):
        done = 0
        for sub in queryset:
            key = sub.approve_and_generate_key()
            done += 1
            self.message_user(request, f'{sub.store_name}: تم التفعيل — الكود: {key}')
        self.message_user(request, f'تم تفعيل {done} اشتراك.')

    @admin.action(description='❌ رفض الطلبات المحددة')
    def reject_subscriptions(self, request, queryset):
        updated = queryset.update(status='rejected')
        self.message_user(request, f'تم رفض {updated} طلب.')
