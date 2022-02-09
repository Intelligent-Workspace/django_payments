from django.conf import settings

def get_backend(**kwargs):
    backend = kwargs.get("backend", None)
    if backend == None:
        return settings.PAYMENT_BACKEND
    return backend