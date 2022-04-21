from django_payments.stripe.payments import *
from django_payments.utils import get_backend

def create_customer(**kwargs):
    if get_backend() == "stripe":
        return stripe_create_customer(**kwargs)
    raise NotImplementedError("Unsupported Payment Backend")

def get_customer_details(**kwargs):
    if get_backend() == "stripe":
        return stripe_get_customer_details(**kwargs)
    raise NotImplementedError("Unsupported Payment Backend")

def create_payment_method(**kwargs):
    if get_backend() == "stripe":
        return stripe_create_payment_method(**kwargs)
    raise NotImplementedError("Unsupported Payment Backend")

def delete_payment_method(**kwargs):
    if get_backend() == "stripe":
        return stripe_delete_payment_method(**kwargs)
    raise NotImplementedError("Unsupported Payment Backend")

def get_payment_method_detail(**kwargs):
    if get_backend() == "stripe":
        return stripe_get_payment_method_detail(**kwargs)
    raise NotImplementedError("Unsupported Payment Backend")

def get_payment_method_details(**kwargs):
    if get_backend() == "stripe":
        return stripe_get_payment_method_details(**kwargs)
    raise NotImplementedError("Unsupported Payment Backend")

def create_charge(**kwargs):
    if get_backend() == "stripe":
        return stripe_create_charge(**kwargs)
    raise NotImplementedError("Unsupported Payment Backend")

def ach_create_auth_token(**kwargs):
    if get_backend() == "stripe":
        return stripe_ach_create_auth_token(**kwargs)
    raise NotImplementedError("Unsupported Payment Backend")

def ach_swap_public_token_backend_token(**kwargs):
    if get_backend() == "stripe":
        return stripe_ach_swap_public_token_backend_token(**kwargs)
    raise NotImplementedError("Unsupported Payment Backend")

def ach_create_charge(**kwargs):
    if get_backend() == "stripe":
        return stripe_ach_create_charge(**kwargs)
    raise NotImplementedError("Unsupported Payment Backend")