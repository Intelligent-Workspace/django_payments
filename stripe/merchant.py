try:
    import stripe
except ImportError:
    raise Exception("Install the stripe SDK")

from django.urls import reverse
from django.conf import settings

from django_payments.models import Merchant

def stripe_merchant_create(**kwargs):
    """
    country - country the connected account should recide in (i.e US)
    card_payments - If True, then card_payments will be accepted
    transfers - If True, then transfers will be accepted
    """
    unique_id = kwargs.get("unique_id", None)
    country = kwargs.get("country", None)
    card_payments = kwargs.get("card_payments", False)
    base_url = kwargs.get("base_url", None)
    provider = "stripe"

    if unique_id == None:
        raise Exception("Invalid request. Please specify the unique_id")
    if country == None:
        raise Exception("Invalid request. Please specify the country")
    capabilities = dict()
    if card_payments:
        capabilities["card_payments"] = {"requested": True}
        capabilities["transfers"] = {"requested": True}
    try:
        merchant_obj = Merchant.objects.get(unique_id=unique_id)
    except Merchant.DoesNotExist:
        account = stripe.Account.create(
            country=country,
            type="standard",
            #capabilities=capabilities
        )
        #Stripe FIXME: Add Error Handling.
        merchant_obj = Merchant(unique_id=unique_id, provider=provider, merchant_info={"account_id": account["id"]})
        merchant_obj.save()
    url = stripe_merchant_account_url(merchant_obj=merchant_obj, base_url=base_url)
    #Stripe FIXME: Add Error Handling
    return url

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
    #Stripe FIXME: Add Error Handling
    account_link = stripe.AccountLink.create(
        account=merchant_obj.merchant_info["account_id"],
        refresh_url=(base_url + reverse(settings.STRIPE_REFRESH_URL)),
        return_url=(base_url + reverse(settings.STRIPE_RETURN_URL)),
        type="account_onboarding",
    )

    return account_link["url"]

def stripe_merchant_configure_bank(**kwargs):
    unique_id = kwargs.get("unique_id", None)
    bank_token = kwargs.get("bank_token", None)
    provider = "stripe"

    try:
        merchant_obj = Merchant.objects.get(unique_id=unique_id, provider=provider)
    except Merchant.DoesNotExist:
        raise Exception("Merchant doesn't exist")
    if merchant_obj.check_bank_acc_done():
        pass
    else:
        bank_obj = stripe.Account.create_external_account(
            merchant_obj.merchant_info["account_id"],
            external_account=bank_token
        )
        merchant_obj.merchant_info["bank_id"] = bank_obj["id"]
        merchant_obj.set_bank_acc_done()
        merchant_obj.save()

def stripe_merchant_fetch_bank_info(**kwargs):
    unique_id = kwargs.get("unique_id", None)
    provider = "stripe"

    try:
        merchant_obj = Merchant.objects.get(unique_id=unique_id, provider=provider)
    except Merchant.DoesNotExist:
        raise Exception("Merchant doesn't exist")
    if merchant_obj.check_bank_acc_done():
        bank_obj = stripe.Account.retrieve_external_account(
            merchant_obj.merchant_info["account_id"],
            merchant_obj.merchant_info["bank_id"]
        )
        #Stripe FIXME: Add Error Handling
        bank_repr = {}
        bank_repr['bank_name'] = bank_obj['bank_name']
        bank_repr['bank_holder_type'] = bank_obj['account_holder_type']
        bank_repr['bank_last4'] = bank_obj['last4']
        return True, bank_repr
    return False, {}

def stripe_sync_merchant_state(**kwargs):
    unique_id = kwargs.get("unique_id", None)
    provider = "stripe"
    try:
        merchant_obj = Merchant.objects.get(unique_id=unique_id, provider=provider)
    except Merchant.DoesNotExist:
        raise Exception("Merchant doesn't exist")
    account_info = stripe.Account.retrieve(merchant_obj.merchant_info["account_id"])
    #Stripe FIXME: Add Error Handling
    eventually_due_requirements = account_info["requirements"]["eventually_due"]
    if len(eventually_due_requirements) == 1 and eventually_due_requirements[0] == "external_account":
        merchant_obj.set_kyc_done()
    if account_info["external_accounts"]["total_count"] > 0:
        merchant_obj.set_bank_acc_done()
        merchant_obj.merchant_info["bank_id"] = account_info['external_accounts']["data"][0]["id"]
    merchant_obj.save()

def stripe_get_merchant_state(**kwargs):
    unique_id = kwargs.get("unique_id", None)
    provider = "stripe"
    try:
        merchant_obj = Merchant.objects.get(unique_id=unique_id, provider=provider)
    except Merchant.DoesNotExist:
        return False, {}
    return True, {"kyc_done": merchant_obj.check_kyc_done(), "bank_acc_done": merchant_obj.check_bank_acc_done()}

def stripe_get_merchant_id(**kwargs):
    unique_id = kwargs.get("unique_id", None)
    provider = "stripe"
    try:
        merchant_obj = Merchant.objects.get(unique_id=unique_id, provider=provider)
    except Merchant.DoesNotExist:
        return ""
    return merchant_obj.merchant_info["account_id"]
