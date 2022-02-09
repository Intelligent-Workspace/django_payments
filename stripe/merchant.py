try:
    import stripe
except ImportError:
    raise Exception("Install the stripe SDK")

from django.urls import reverse
from django.conf import settings

from django_payments.models import Merchant
from django_payments.stripe.utils import _stripe_api_call

stripe.api_key = settings.PAYMENT_PRIVATE_KEY["stripe"]
stripe.max_network_retries = 2

def stripe_merchant_create(**kwargs):
    """
    country - country the connected account should recide in (i.e US)
    transfers - If True, then transfers will be accepted
    """
    unique_id = kwargs.get("unique_id", None)
    country = kwargs.get("country", None)
    base_url = kwargs.get("base_url", None)
    provider = "stripe"

    if unique_id == None:
        raise Exception("Invalid request. Please specify the unique_id")
    if country == None:
        raise Exception("Invalid request. Please specify the country")
    if country != "us":
        raise Exception("Invalid request. Only 'US' is supported as a country")

    try:
        merchant_obj = Merchant.objects.get(unique_id=unique_id, provider=provider)
    except Merchant.DoesNotExist:
        response = _stripe_api_call(stripe.Account.create, country=country, type="standard")
        if not response['is_success']:
            return False, {"reason": "unexpected_error"}
        account = response["resource"]
        merchant_obj = Merchant(unique_id=unique_id, provider=provider, merchant_info={"account_id": account["id"]})
        merchant_obj.save()
    is_success, url = stripe_merchant_account_url(merchant_obj=merchant_obj, base_url=base_url)
    return is_success, url

def stripe_merchant_account_url(**kwargs):
    unique_id = kwargs.get("unique_id", None)
    merchant_obj = kwargs.get("merchant_obj", None)
    base_url = kwargs.get("base_url", None)
    provider = "stripe"

    if base_url == None:
        raise Exception("Invalid request. Please specify a base_url")
    if merchant_obj == None:
        if unique_id == None:
            raise Exception("Invalid request. Please specify the unique_id")
        try:
            merchant_obj = Merchant.objects.get(unique_id=unique_id, provider=provider)
        except Merchant.DoesNotExist:
            raise Exception("Merchant doesn't exist")

    response = _stripe_api_call(stripe.AccountLink.create,
        account=merchant_obj.merchant_info["account_id"],
        refresh_url=(base_url + reverse(settings.PAYMENT_MISC_SETTINGS["stripe"]["refresh_url"])),
        return_url=(base_url + reverse(settings.PAYMENT_MISC_SETTINGS["stripe"]["return_url"])),
        type="account_onboarding"
    )
    if not response['is_success']:
        return False, {"reason": "unexpected_error"}
    return True, response["resource"]["url"]

def stripe_merchant_sync(**kwargs):
    unique_id = kwargs.get("unique_id", None)
    provider = "stripe"

    if unique_id == None:
        raise Exception("Invalid request. Please specify the unique_id")

    try:
        merchant_obj = Merchant.objects.get(unique_id=unique_id, provider=provider)
    except Merchant.DoesNotExist:
        return False, {"reason": "merchant_not_exist"}
    response = _stripe_api_call(stripe.Account.retrieve, id=merchant_obj.merchant_info["account_id"])
    if not response['is_success']:
        return False, {"reason": "unexpected_error"}
    account = response['resource']    
    merchant_obj.set_is_setup_started()

    if account["charges_enabled"] == True and account["details_submitted"] == True and account["payouts_enabled"]:
        merchant_obj.set_is_setup_finished()
    merchant_obj.save()
    return True, {}

def stripe_merchant_state(**kwargs):
    unique_id = kwargs.get("unique_id", None)
    provider = "stripe"

    if unique_id == None:
        raise Exception("Invalid request. Please specify the unique_id")
    
    try:
        merchant_obj = Merchant.objects.get(unique_id=unique_id, provider=provider)
    except Merchant.DoesNotExist:
        return True, {"status": "setup_not_started"}

    if merchant_obj.check_is_setup_finished():
        return True, {"status": "setup_finished"}
    elif merchant_obj.check_is_setup_started():
        return True, {"status": "setup_started"}
    else:
        return True, {"status": "setup_not_started"}