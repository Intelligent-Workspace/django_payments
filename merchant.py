from django_payments.stripe.merchant import *

from django.conf import settings

def merchant_create(**kwargs):
    if settings.PAYMENT_BACKEND == "stripe":
        return stripe_merchant_create(**kwargs)
    raise NotImplementedError("Unsupported Payment Backend")

def merchant_account_url(**kwargs):
    if settings.PAYMENT_BACKEND == "stripe":
        return stripe_merchant_account_url(**kwargs)
    raise NotImplementedError("Unsupported Payment Backend")

def sync_merchant(**kwargs):
    if settings.PAYMENT_BACKEND == "stripe":
        return stripe_sync_merchant(**kwargs)
    raise NotImplementedError("Unsupported Payment Backend")

def merchant_state(**kwargs):
    if settings.PAYMENT_BACKEND == "stripe":
        return stripe_merchant_state(**kwargs)
    raise NotImplementedError("Unsupported Payment Backend")

