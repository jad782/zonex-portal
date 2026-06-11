# -*- coding: utf-8 -*-
from datetime import timedelta

from django.db import models
from django.utils import timezone

from .licensekey import generate_license_key


# ── الباقات: المدة بالأيام + السعر بالدولار ──
PLANS = {
    'monthly':   {'label': 'شهري',        'days': 30,  'price': 50,  'months': 1},
    'quarterly': {'label': '٣ أشهر',      'days': 90,  'price': 135, 'months': 3},
    'yearly':    {'label': 'سنوي',        'days': 365, 'price': 500, 'months': 12},
}

PLAN_CHOICES = [(k, v['label']) for k, v in PLANS.items()]

COUNTRY_CHOICES = [
    ('SY', 'سوريا'),
    ('TR', 'تركيا'),
    ('OTHER', 'دولة أخرى'),
]

PAYMENT_CHOICES = [
    ('shamcash', 'شام كاش (سوريا)'),
    ('kuwaitturk', 'Kuwait Türk (تركيا)'),
    ('other', 'طريقة أخرى'),
]

STATUS_CHOICES = [
    ('pending', 'بانتظار الدفع'),
    ('submitted', 'بانتظار المراجعة'),
    ('approved', 'مُفعّل'),
    ('rejected', 'مرفوض'),
]


class Subscription(models.Model):
    store_name = models.CharField(max_length=120, verbose_name="اسم المحل")
    owner_name = models.CharField(max_length=120, verbose_name="اسم صاحب المحل")
    phone = models.CharField(max_length=40, verbose_name="رقم الهاتف / واتساب")
    email = models.EmailField(blank=True, null=True, verbose_name="البريد (اختياري)")
    country = models.CharField(max_length=10, choices=COUNTRY_CHOICES, default='SY', verbose_name="الدولة")

    plan = models.CharField(max_length=20, choices=PLAN_CHOICES, default='monthly', verbose_name="الباقة")
    price = models.FloatField(default=0, verbose_name="السعر ($)")

    payment_method = models.CharField(max_length=20, choices=PAYMENT_CHOICES, blank=True, null=True, verbose_name="طريقة الدفع")
    transaction_id = models.CharField(max_length=120, blank=True, null=True, verbose_name="رقم العملية")
    receipt_image = models.ImageField(upload_to='receipts/', blank=True, null=True, verbose_name="صورة الإيصال")

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="الحالة")
    license_key = models.CharField(max_length=60, blank=True, null=True, verbose_name="كود التفعيل")
    expires_at = models.DateField(blank=True, null=True, verbose_name="تاريخ الانتهاء")

    admin_note = models.CharField(max_length=255, blank=True, null=True, verbose_name="ملاحظة الإدارة")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الطلب")
    approved_at = models.DateTimeField(blank=True, null=True, verbose_name="تاريخ التفعيل")

    class Meta:
        verbose_name = "اشتراك"
        verbose_name_plural = "الاشتراكات"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.store_name} ({self.get_plan_display()}) - {self.get_status_display()}"

    @property
    def plan_days(self):
        return PLANS.get(self.plan, PLANS['monthly'])['days']

    def approve_and_generate_key(self):
        """يفعّل الاشتراك ويولّد كود التفعيل المربوط باسم المحل."""
        self.status = 'approved'
        self.save()   # save() يولّد الكود تلقائياً (تحت)
        return self.license_key

    def save(self, *args, **kwargs):
        """ضمان: أي اشتراك حالته 'approved' لازم يكون عنده كود تفعيل تلقائياً —
        بغض النظر عن طريقة الموافقة (زر، أكشن، أو تغيير الحالة يدوياً)."""
        if self.status == 'approved' and not self.license_key:
            self.expires_at = timezone.localdate() + timedelta(days=self.plan_days)
            self.license_key = generate_license_key(self.store_name, self.expires_at)
            if not self.approved_at:
                self.approved_at = timezone.now()
        super().save(*args, **kwargs)
