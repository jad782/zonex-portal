# -*- coding: utf-8 -*-
"""توليد كود التفعيل — نفس خوارزمية التطبيق المحلي (cafe/models.py).
لازم يكون LICENSE_SECRET هنا = نفسه في التطبيق المحلي حتى يقبل الكود."""
import hashlib
import hmac

from django.conf import settings


def normalize_customer_name(customer_name):
    return " ".join((customer_name or "").strip().upper().split())


def _signature(customer_name, expires_yyyymmdd):
    normalized = normalize_customer_name(customer_name)
    raw = f"{normalized}|{expires_yyyymmdd}".encode("utf-8")
    secret = settings.LICENSE_SECRET.encode("utf-8")
    return hmac.new(secret, raw, hashlib.sha256).hexdigest()[:16].upper()


def generate_license_key(customer_name, expire_date):
    if hasattr(expire_date, "strftime"):
        yyyymmdd = expire_date.strftime("%Y%m%d")
    else:
        yyyymmdd = str(expire_date).replace("-", "")
    return f"ZX-{yyyymmdd}-{_signature(customer_name, yyyymmdd)}"
