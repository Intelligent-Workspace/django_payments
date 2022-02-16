from django.shortcuts import render
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils.module_loading import import_string
from django.conf import settings

from django_payments.models import Customer, PaymentMethod

import stripe
from threading import Thread

def stripe_process(webhook_event, callback):
    if webhook_event['type'] == "setup_intent.succeeded":
        try:
            customer_obj = Customer.objects.get(customer_info__type="stripe", customer_info__customer_id=webhook_event.data.object.customer)
        except Customer.DoesNotExist:
            pass
        else:
            d_payment_method = {"payment_method_id": webhook_event.data.object.payment_method}
            payment_method_object = PaymentMethod(merchant_id=customer_obj.merchant_id, unique_id=customer_obj.unique_id,
                payment_method_info=d_payment_method)
            payment_method_object.save()

            params = dict()
            params['merchant_id'] = customer_obj.merchant_id
            params['customer_id'] = customer_obj.unique_id
            params['payment_method_id'] = payment_method_obj.id
            params['event'] = "payment_method_success"
            callback(params)
    elif webhook_event['type'] == "account.updated":
        try:
            merchant_obj = Merchant.objects.get(provider="stripe", merchant_info__account_id=webhook_event.data.object.id)
        except Merchant.DoesNotExist:
            pass
        else:
            account = webhook_event.data.object
            merchant_obj.set_is_setup_started()
            if account["charges_enabled"] == True and account["details_submitted"] == True and account["payouts_enabled"] == True:
                merchant_obj.set_is_setup_finished()
            merchant_obj.save()

            params = dict()
            params['merchant_id'] = merchant_obj.unique_id
            params['event'] = "merchant_account_success"
            callback(params)
    elif webhook_event['type'] == "payment_intent.succeeded":
        try:
            customer_obj = Customer.objects.get(customer_info__type="stripe", customer_info__customer_id=webhook_event.data.object.customer)
        except Customer.DoesNotExist:
            pass
        else:
            from django_payments.payments import get_payment_method_detail
            params = dict()
            params['merchant_id'] = customer_obj.merchant_id
            params['customer_id'] = customer_obj.unique_id
            params['metadata'] = webhook_event.data.object.metadata
            params['event'] = "charge_success"

            is_success, response = get_payment_method_detail(merchant_id=params['merchant_id'], 
                payment_method_id=webhook_event.data.object.payment_method)
            params['payment_method'] = "unknown"
            if is_success:
                params['payment_method'] = response["type"]

            callback(params)

# Create your views here.
@csrf_exempt
@require_POST
def webhook_stripe(request):
    endpoint_secret = settings.PAYMENT_MISC_SETTINGS["stripe"]["webhook_signing_secret"] 
    event = None
    payload = request.body
    sig_header = request.headers['STRIPE_SIGNATURE']

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except ValueError as e:
        raise e
    except stripe.error.SignatureVerificationError as e:
        raise e
    callback = import_string(settings.PAYMENT_WEBHOOK_PROCESS["stripe"])
    Thread(target=stripe_process, args=(event, callback)).start()
    return HttpResponse("OK")