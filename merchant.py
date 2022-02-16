from django_payments.stripe.merchant import *
from django_payments.utils import get_backend

def merchant_create(**kwargs):
    if get_backend() == "stripe":
        return stripe_merchant_create(**kwargs)
    raise NotImplementedError("Unsupported Payment Backend")

def merchant_account_url(**kwargs):
    if get_backend() == "stripe":
        return stripe_merchant_account_url(**kwargs)
    raise NotImplementedError("Unsupported Payment Backend")

def merchant_sync(**kwargs):
    if get_backend() == "stripe":
        return stripe_merchant_sync(**kwargs)
    raise NotImplementedError("Unsupported Payment Backend")

def merchant_state(**kwargs):
    if get_backend() == "stripe":
        return stripe_merchant_state(**kwargs)
    raise NotImplementedError("Unsupported Payment Backend")

def merchant_info(**kwargs):
    if get_backend() == "stripe":
        return stripe_merchant_info(**kwargs)
    raise NotImplementedError("Unsupported Payment Backend")

