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

# معلومات الدفع الحقيقية
PAYMENT_INFO = {
    'shamcash': {
        'title': 'شام كاش (سوريا)',
        'lines': [
            'للدفع داخل سوريا تواصل معنا على واتساب: 0090 555 151 7264',
            'منعطيك طريقة الدفع والمبلغ بالليرة السورية حسب سعر اليوم.',
            'بعد الاتفاق، أكمل الطلب وارفع صورة الإيصال.',
        ],
    },
    'kuwaitturk': {
        'title': 'Kuwait Türk (تركيا)',
        'lines': [
            'IBAN (ليرة تركية ₺): TR04 0020 5000 0990 7839 6000 01',
            'IBAN (دولار $): TR90 0020 5000 0990 7839 6001 02',
            'SWIFT / BIC: KTEFTRISXXX',
            'الاسم / Ad: JAD ALSAYALEH',
            'بعد التحويل أدخل رقم العملية وارفع صورة الإيصال (dekont).',
        ],
    },
    'other': {
        'title': 'طريقة أخرى',
        'lines': ['تواصل معنا على واتساب 0090 555 151 7264 للاتفاق على طريقة الدفع.'],
    },
}


# رقم واتساب للتواصل/الديمو — عدّله برقمك الحقيقي (صيغة دولية بدون + أو 00)
WHATSAPP_NUMBER = '905551517264'

# أسماء تجارية ووصف لكل باقة (تظهر بالموقع فقط)
PLAN_MARKETING = {
    'monthly':   {'tier': 'Starter', 'desc': 'للمحل الصغير — يبدأ معك بأقل تكلفة.'},
    'quarterly': {'tier': 'Pro',     'desc': 'للمحل المتوسط — توفير أكثر على ٣ أشهر.'},
    'yearly':    {'tier': 'Annual',  'desc': 'أفضل سعر — شهرين مجاناً بالاشتراك السنوي.'},
}


def landing(request):
    plans = []
    for key, data in PLANS.items():
        mk = PLAN_MARKETING.get(key, {})
        plans.append({
            'key': key,
            'label': data['label'],
            'tier': mk.get('tier', ''),
            'desc': mk.get('desc', ''),
            'price': data['price'],
            'months': data['months'],
            'monthly_equiv': round(data['price'] / data['months'], 1),
            'highlight': key == 'yearly',
            'free_months': 2 if key == 'yearly' else 0,
        })
    return render(request, 'portal/landing.html', {
        'plans': plans,
        'whatsapp': WHATSAPP_NUMBER,
    })


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

        # منع التكرار: اسم المحل + الإيميل + رقم الهاتف (اسم صاحب المحل يجوز يتكرر)
        dup_error = None
        if not store_name or not owner_name or not phone:
            dup_error = 'اكتب اسم المحل واسم صاحبه ورقم الهاتف.'
        elif Subscription.objects.filter(store_name__iexact=store_name).exists():
            dup_error = 'اسم المحل مستعمل من قبل. اختر اسماً آخر.'
        elif phone and Subscription.objects.filter(phone=phone).exists():
            dup_error = 'رقم الهاتف مستعمل من قبل.'
        elif email and Subscription.objects.filter(email__iexact=email).exists():
            dup_error = 'البريد الإلكتروني مستعمل من قبل.'

        if dup_error:
            messages.error(request, dup_error)
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
        receipt = request.FILES.get('receipt_image')

        if not receipt:
            messages.error(request, 'ارفع صورة الإيصال.')
        else:
            sub.payment_method = method
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


def license_status(request):
    """يرجّع حالة الاشتراك للبرنامج المحلي (هل ما زال مفعّلاً؟).
    يُستخدم للإيقاف عن بُعد: لو صار 'rejected' أو منتهي → active=False فيتقفل البرنامج."""
    from .licensekey import normalize_customer_name
    from django.utils import timezone as _tz
    store = (request.GET.get('store_name') or '').strip()
    key = (request.GET.get('license_key') or '').strip().upper()

    if not store or not key:
        return JsonResponse({'ok': False, 'error': 'missing'}, status=400)

    sub = Subscription.objects.filter(license_key=key).first()
    if not sub or normalize_customer_name(sub.store_name) != normalize_customer_name(store):
        # كود غير معروف بالموقع — لا نتدخّل (الكود موقّع محلياً)
        return JsonResponse({'ok': False, 'unknown': True})

    not_expired = (sub.expires_at is None) or (sub.expires_at >= _tz.localdate())
    active = (sub.status == 'approved') and not_expired

    return JsonResponse({
        'ok': True,
        'status': sub.status,
        'active': active,
        'expires_at': str(sub.expires_at) if sub.expires_at else '',
    })


@require_POST
def claim_machine(request):
    """يربط الاشتراك بجهاز واحد. أول تفعيل يثبّت معرّف الجهاز.
    أي جهاز آخر بنفس الكود → ok=False, error='bound_other' (إلا بعد إعادة التعيين من الإدارة)."""
    from .licensekey import normalize_customer_name
    try:
        import json as _json
        data = _json.loads(request.body.decode('utf-8') or '{}')
    except Exception:
        data = {}

    store = (data.get('store_name') or '').strip()
    key = (data.get('license_key') or '').strip().upper()
    machine = (data.get('machine_id') or '').strip()

    if not store or not key or not machine:
        return JsonResponse({'ok': False, 'error': 'missing'}, status=400)

    sub = Subscription.objects.filter(license_key=key, status='approved').first()
    if not sub or normalize_customer_name(sub.store_name) != normalize_customer_name(store):
        # الكود غير معروف بالموقع — لا نمنع (الكود موقّع محلياً)، نسمح
        return JsonResponse({'ok': True, 'unknown': True})

    if not sub.machine_id:
        sub.machine_id = machine
        sub.save(update_fields=['machine_id'])
        return JsonResponse({'ok': True, 'bound': True})

    if sub.machine_id == machine:
        return JsonResponse({'ok': True})

    return JsonResponse({'ok': False, 'error': 'bound_other'})


@require_POST
@user_passes_test(lambda u: u.is_staff)
def api_reset_machine(request, sub_id):
    """إعادة تعيين الجهاز المربوط (لو خربت شاشة الزبون) — للإدارة فقط."""
    sub = get_object_or_404(Subscription, id=sub_id)
    sub.machine_id = None
    sub.save(update_fields=['machine_id'])
    return JsonResponse({'status': 'success'})


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
    from django.utils import timezone as _tz
    from datetime import timedelta as _td
    today = _tz.localdate()
    soon = today + _td(days=7)

    flt = request.GET.get('f', 'review')
    qs = Subscription.objects.all()
    if flt == 'review':
        qs = qs.filter(status='submitted')
    elif flt == 'pending':
        qs = qs.filter(status='pending')
    elif flt == 'approved':
        qs = qs.filter(status='approved')
    elif flt == 'expiring':
        qs = qs.filter(status='approved', expires_at__gte=today, expires_at__lte=soon)
    qs = qs.order_by('-created_at')

    counts = {
        'review': Subscription.objects.filter(status='submitted').count(),
        'pending': Subscription.objects.filter(status='pending').count(),
        'approved': Subscription.objects.filter(status='approved').count(),
        'expiring': Subscription.objects.filter(
            status='approved', expires_at__gte=today, expires_at__lte=soon).count(),
        'all': Subscription.objects.count(),
    }
    return render(request, 'portal/manage.html', {
        'subs': qs,
        'filter': flt,
        'counts': counts,
        'today': today,
    })


# نسخة البرنامج الأحدث — ارفعها مع كل إصدار جديد
LATEST_APP_VERSION = "1.1.5"


def app_version(request):
    """يخبر البرنامج بأحدث إصدار متوفّر ورابط التحميل (للتحديث التلقائي)."""
    return JsonResponse({
        'version': LATEST_APP_VERSION,
        'url': 'https://zonexsys.com/download/',
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
