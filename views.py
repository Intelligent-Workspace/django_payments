from django.shortcuts import render
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils.module_loading import import_string
from django.conf import settings

from django_payments.models import Customer, PaymentMethod, Merchant

import stripe
from threading import Thread

def stripe_process(webhook_event, callback):
    if webhook_event['type'] == "payment_method.attached":
        try:
            customer_obj = Customer.objects.get(customer_info__type="stripe", customer_info__customer_id=webhook_event.data.object.customer)
        except Customer.DoesNotExist:
            pass
        else:
            try:
                payment_method_object = PaymentMethod.objects.get(merchant_id=customer_obj.merchant_id, unique_id=customer_obj.unique_id, 
                    payment_method_info__payment_method_id=webhook_event.data.object.id)
            except PaymentMethod.DoesNotExist:
                d_payment_method = {"payment_method_id": webhook_event.data.object.id, "payment_method_type": "payment_method", "payment_method": ""}
                if "card" in webhook_event.data.object:
                    d_payment_method["payment_method"] = "card"
                elif "us_bank_account" in webhook_event.data.object:
                    d_payment_method["payment_method"] = "ach_debit"
                payment_method_object = PaymentMethod(merchant_id=customer_obj.merchant_id, unique_id=customer_obj.unique_id,
                    payment_method_info=d_payment_method)
                payment_method_object.save()

            params = dict()
            params['merchant_id'] = customer_obj.merchant_id
            params['customer_id'] = customer_obj.unique_id
            params['payment_method_id'] = payment_method_object.id
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
            if account['requirements']['disabled_reason'] is not None:
                if account['requirements']['disabled_reason'] == "requirements.past_due":
                    merchant_obj.merchant_info["verification_status"] = "requires_info"
                elif account['requirements']['disabled_reason'] == "requirements.pending_verification":
                    merchant_obj.merchant_info['verification_status'] = "verify"
                elif "rejected" in account['requirements']['disabled_reason']:
                    merchant_obj.merchant_info['verification_status'] = "rejected"
                elif account['requirements']['disabled_reason'] == "listed" or account['requirements']['disabled_reason'] == "under_review":
                    merchant_obj.merchant_info['verification_status'] = "under_review"
                elif account['requirements']['disabled_reason'] == "other":
                    merchant_obj.merchant_info['verification_status'] = "under_review_disable"
                else:
                    pass
            if account["charges_enabled"] == True and account["details_submitted"] == True and account["payouts_enabled"] == True:
                merchant_obj.set_is_setup_finished()
            merchant_obj.save()

            params = dict()
            params['merchant_id'] = merchant_obj.unique_id
            params['event'] = "merchant_account_success"
            callback(params)
    elif webhook_event['type'] == "charge.succeeded":
        try:
            customer_obj = Customer.objects.get(customer_info__type="stripe", customer_info__customer_id=webhook_event.data.object.customer)
        except Customer.DoesNotExist:
            pass
        else:
            params = dict()
            params['merchant_id'] = customer_obj.merchant_id
            params['customer_id'] = customer_obj.unique_id
            params['metadata'] = webhook_event.data.object.metadata
            params['event'] = "charge_success"
            params['payment_method'] = webhook_event.data.object.payment_method_details.type
            callback(params)
    elif webhook_event['type'] == "charge.pending":
        try:
            customer_obj = Customer.objects.get(customer_info__type="stripe", customer_info__customer_id=webhook_event.data.object.customer)
        except Customer.DoesNotExist:
            pass
        else:
            params = dict()
            params['merchant_id'] = customer_obj.merchant_id
            params['customer_id'] = customer_obj.unique_id
            params['metadata'] = webhook_event.data.object.metadata
            params['event'] = "charge_processing"
            callback(params)
    elif webhook_event['type'] == "charge.failed":
        """
        fail_code
            - debit_not_authorized - Customer has notified their bank that this payment was unauthorized
            - insufficient_funds - Customer has insufficient funds to cover this payment
            - no_account - Customer bank account could not be located
            - account_closed - Customer bank account has been closed
        """
        try:
            customer_obj = Customer.objects.get(customer_info__type="stripe", customer_info__customer_id=webhook_event.data.object.customer)
        except Customer.DoesNotExist:
            pass
        else:
            params = dict()
            params['merchant_id'] = customer_obj.merchant_id
            params['customer_id'] = customer_obj.unique_id
            params['metadata'] = webhook_event.data.object.metadata
            params['fail_code'] = webhook_event.data.object.failure_code
            params['fail_message'] = webhook_event.data.object.failure_message
            params['event'] = "charge_fail"
            callback(params)
    elif webhook_event['type'] == "financial_connections.account.created":
        try:
            customer_obj = Customer.objects.get(customer_info__type="stripe", customer_info__customer_id=webhook_event.data.object.account_holder.customer)
        except Customer.DoesNotExist:
            pass
        else:
            params = dict()
            params['merchant_id'] = customer_obj.merchant_id
            params['customer_id'] = customer_obj.unique_id
            params['bank'] = webhook_event.data.object.institution_name
            params['last4'] = webhook_event.data.object.last4
            params['event'] = "bank_account_verify"
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