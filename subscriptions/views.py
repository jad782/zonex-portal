# -*- coding: utf-8 -*-
import os
from django.conf import settings as dj_settings
from django.http import FileResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from .models import Subscription, PLANS, PLAN_CHOICES, COUNTRY_CHOICES, PAYMENT_CHOICES

# ⚠️ معلومات الدفع — عدّلها لاحقاً بأرقامك الحقيقية
PAYMENT_INFO = {
    'shamcash': {
        'title': 'شام كاش (سوريا)',
        'lines': [
            'رقم الحساب: 0000000000  (ضع رقمك)',
            'الاسم: ZONE X',
            'بعد التحويل أدخل رقم العملية وارفع صورة الإيصال.',
        ],
    },
    'kuwaitturk': {
        'title': 'Kuwait Türk (تركيا)',
        'lines': [
            'IBAN: TR00 0000 0000 0000 0000 0000 00  (IBAN حسابك)',
            'Ad / الاسم: ZONE X',
            'Havale sonrası işlem no girin ve dekontu yükleyin.',
        ],
    },
    'other': {
        'title': 'طريقة أخرى',
        'lines': ['تواصل معنا على واتساب للاتفاق على طريقة الدفع.'],
    },
}


def landing(request):
    plans = []
    for key, data in PLANS.items():
        plans.append({
            'key': key,
            'label': data['label'],
            'price': data['price'],
            'months': data['months'],
            'monthly_equiv': round(data['price'] / data['months'], 1),
            'highlight': key == 'yearly',
            'free_months': 2 if key == 'yearly' else 0,
        })
    return render(request, 'portal/landing.html', {'plans': plans})


def signup(request):
    plan = request.GET.get('plan', 'monthly')
    if plan not in PLANS:
        plan = 'monthly'

    if request.method == 'POST':
        plan = request.POST.get('plan', 'monthly')
        if plan not in PLANS:
            plan = 'monthly'

        store_name = (request.POST.get('store_name') or '').strip()
        owner_name = (request.POST.get('owner_name') or '').strip()
        manager_password = (request.POST.get('manager_password') or '').strip()
        phone = (request.POST.get('phone') or '').strip()
        email = (request.POST.get('email') or '').strip()
        country = request.POST.get('country', 'SY')

        if not store_name or not owner_name or not phone:
            messages.error(request, 'اكتب اسم المحل واسم صاحبه ورقم الهاتف.')
        else:
            sub = Subscription.objects.create(
                store_name=store_name,
                owner_name=owner_name,
                manager_password=manager_password or '1234',
                phone=phone,
                email=email or None,
                country=country,
                plan=plan,
                price=PLANS[plan]['price'],
                status='pending',
            )
            return redirect('pay', sub_id=sub.id)

    return render(request, 'portal/signup.html', {
        'plan': plan,
        'plan_info': PLANS[plan],
        'plans': PLAN_CHOICES,
        'countries': COUNTRY_CHOICES,
    })


def pay(request, sub_id):
    sub = get_object_or_404(Subscription, id=sub_id)

    if sub.status in ('approved',):
        return redirect('status_detail', sub_id=sub.id)

    if request.method == 'POST':
        method = request.POST.get('payment_method', 'shamcash')
        transaction_id = (request.POST.get('transaction_id') or '').strip()
        receipt = request.FILES.get('receipt_image')

        if not transaction_id or not receipt:
            messages.error(request, 'أدخل رقم العملية وارفع صورة الإيصال.')
        else:
            sub.payment_method = method
            sub.transaction_id = transaction_id
            sub.receipt_image = receipt
            sub.status = 'submitted'
            sub.save()
            return redirect('thanks', sub_id=sub.id)

    return render(request, 'portal/payment.html', {
        'sub': sub,
        'methods': PAYMENT_CHOICES,
        'payment_info': PAYMENT_INFO,
    })


def thanks(request, sub_id):
    sub = get_object_or_404(Subscription, id=sub_id)
    return render(request, 'portal/thanks.html', {'sub': sub})


def store_config(request):
    """يرجّع إعدادات المحل (كلمة سر المدير، اسم صاحب المحل) للتطبيق المحلي وقت التفعيل.
    يتطلب اسم المحل + كود تفعيل صحيح ومفعّل."""
    from .licensekey import normalize_customer_name
    store = (request.GET.get('store_name') or '').strip()
    key = (request.GET.get('license_key') or '').strip().upper()

    if not store or not key:
        return JsonResponse({'ok': False, 'error': 'missing params'}, status=400)

    sub = Subscription.objects.filter(license_key=key, status='approved').first()
    if not sub or normalize_customer_name(sub.store_name) != normalize_customer_name(store):
        return JsonResponse({'ok': False})

    return JsonResponse({
        'ok': True,
        'manager_password': sub.manager_password or '1234',
        'owner_name': sub.owner_name or '',
    })


def download_app(request):
    """تحميل برنامج ZONE X.
    1) إذا في رابط خارجي (Google Drive) محدّد بـ .env → يحوّل إليه.
    2) إذا ملف التثبيت مرفوع على السيرفر (downloads/ZONE_X_Setup.exe) → ينزّله.
    3) غير هيك → صفحة "قيد التجهيز"."""
    if dj_settings.DOWNLOAD_URL:
        return redirect(dj_settings.DOWNLOAD_URL)

    path = os.path.join(dj_settings.BASE_DIR, 'downloads', 'ZONE_X_Setup.exe')
    if os.path.exists(path):
        return FileResponse(open(path, 'rb'), as_attachment=True, filename='ZONE_X_Setup.exe')

    return render(request, 'portal/download_pending.html')


def status_detail(request, sub_id):
    sub = get_object_or_404(Subscription, id=sub_id)
    return render(request, 'portal/status.html', {
        'sub': sub,
        'download_url': dj_settings.DOWNLOAD_URL,
    })


def status_lookup(request):
    sub = None
    if request.method == 'POST':
        phone = (request.POST.get('phone') or '').strip()
        sub = Subscription.objects.filter(phone=phone).order_by('-created_at').first()
        if not sub:
            messages.error(request, 'ما لقينا طلب بهذا الرقم.')
    return render(request, 'portal/status_lookup.html', {'sub': sub})


# ─────────── لوحة الإدارة (سلسة) ───────────

def _is_staff(user):
    return user.is_active and user.is_staff


def manage_login(request):
    if request.user.is_authenticated and request.user.is_staff:
        return redirect('manage')
    error = None
    if request.method == 'POST':
        user = authenticate(
            request,
            username=request.POST.get('username'),
            password=request.POST.get('password'),
        )
        if user is not None and user.is_staff:
            login(request, user)
            return redirect('manage')
        error = 'بيانات الدخول غير صحيحة أو ليست لمدير.'
    return render(request, 'portal/manage_login.html', {'error': error})


def manage_logout(request):
    logout(request)
    return redirect('manage_login')


@login_required(login_url='manage_login')
@user_passes_test(_is_staff, login_url='manage_login')
def manage(request):
    flt = request.GET.get('f', 'review')
    qs = Subscription.objects.all()
    if flt == 'review':
        qs = qs.filter(status='submitted')
    elif flt == 'pending':
        qs = qs.filter(status='pending')
    elif flt == 'approved':
        qs = qs.filter(status='approved')
    qs = qs.order_by('-created_at')

    counts = {
        'review': Subscription.objects.filter(status='submitted').count(),
        'pending': Subscription.objects.filter(status='pending').count(),
        'approved': Subscription.objects.filter(status='approved').count(),
        'all': Subscription.objects.count(),
    }
    return render(request, 'portal/manage.html', {
        'subs': qs,
        'filter': flt,
        'counts': counts,
    })


@require_POST
@login_required(login_url='manage_login')
@user_passes_test(_is_staff, login_url='manage_login')
def api_approve(request, sub_id):
    sub = get_object_or_404(Subscription, id=sub_id)
    key = sub.approve_and_generate_key()
    return JsonResponse({
        'status': 'success',
        'license_key': key,
        'expires_at': str(sub.expires_at),
        'store_name': sub.store_name,
    })


@require_POST
@login_required(login_url='manage_login')
@user_passes_test(_is_staff, login_url='manage_login')
def api_reject(request, sub_id):
    sub = get_object_or_404(Subscription, id=sub_id)
    sub.status = 'rejected'
    sub.save(update_fields=['status'])
    return JsonResponse({'status': 'success'})
