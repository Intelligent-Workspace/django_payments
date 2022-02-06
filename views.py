from django.shortcuts import render
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from django_payments.models import Customer, PaymentMethod

import stripe

# Create your views here.
@csrf_exempt
@require_POST
def webhook_stripe(request):
    endpoint_secret = "whsec_67fda2de794579850501884a2c39f477dafe8f679d7764c4dd4e77be38f3f48f"
    event = None
    payload = request.body
    sig_header = request.headers['STRIPE_SIGNATURE']

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except ValueError as e:
        raise e
    except stripe.error.SignatureVerificationError as e:
        raise e

    if event['type'] == "setup_intent.succeeded":
        try:
            customer_obj = Customer.objects.get(customer_info__type="stripe", customer_info__customer_id=event.data.object.customer)
        except Customer.DoesNotExist:
            pass
        else:
            d_payment_method = {"payment_method_id": event.data.object.payment_method}
            payment_method_object = PaymentMethod(merchant_id=customer_obj.merchant_id, unique_id=customer_obj.unique_id,
                payment_method_info=d_payment_method)
            payment_method_object.save()

    print(event['type'])
    return HttpResponse("OK")

def webhook_stripe_return(request):
    return HttpResponse("Stripe Return Url")

def webhook_stripe_refresh(request):
    return HttpResponse("Stripe Refresh Url")