from django_payments.stripe.payments import *

from django.conf import settings

def create_customer(**kwargs):
    if settings.PAYMENT_BACKEND == "stripe":
        return stripe_create_customer(**kwargs)
    raise NotImplementedError("Unsupported Payment Backend")

def get_customer_details(**kwargs):
    if settings.PAYMENT_BACKEND == "stripe":
        return stripe_get_customer_details(**kwargs)
    raise NotImplementedError("Unsupported Payment Backend")

def create_payment_method(**kwargs):
    if settings.PAYMENT_BACKEND == "stripe":
        return stripe_create_payment_method(**kwargs)
    raise NotImplementedError("Unsupported Payment Backend")

def get_payment_method_detail(**kwargs):
    if settings.PAYMENT_BACKEND == "stripe":
        return stripe_get_payment_method_detail(**kwargs)
    raise NotImplementedError("Unsupported Payment Backend")

def get_payment_method_details(**kwargs):
    if settings.PAYMENT_BACKEND == "stripe":
        return stripe_get_payment_method_details(**kwargs)
    raise NotImplementedError("Unsupported Payment Backend")

def create_charge(**kwargs):
    if settings.PAYMENT_BACKEND == "stripe":
        return stripe_create_charge(**kwargs)
    raise NotImplementedError("Unsupported Payment Backend")