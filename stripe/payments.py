try:
    import stripe
except ImportError:
    raise Exception("Install the stripe SDK")

from django.conf import settings

from django_payments.models import Merchant, Customer, PaymentMethod
from django_payments.stripe.utils import _stripe_api_call

stripe.api_key = settings.PAYMENT_PRIVATE_KEY["stripe"]
stripe.max_network_retries = 2

def __stripe_payment_method_pretty(payment_obj):
    if "card" in payment_obj:
        payment_method_id = None
        try:
            payment_method_obj = PaymentMethod.objects.get(payment_method_info__payment_method_type="payment_method", 
                payment_method_info__payment_method_id=payment_obj["id"])
        except PaymentMethod.DoesNotExist:
            pass
        else:
            payment_method_id = payment_method_obj.id
        return {
            "id": payment_method_id,
            "type": "card",
            "payment_method_type": "card",
            "brand": payment_obj["card"]["brand"],
            "last4": payment_obj["card"]["last4"],
            "exp_month": payment_obj["card"]["exp_month"],
            "exp_year": payment_obj["card"]["exp_year"]
        }
    elif "us_bank_account" in payment_obj:
        payment_method_id = None
        try:
            payment_method_obj = PaymentMethod.objects.get(payment_method_info__payment_method_type="payment_method", 
                payment_method_info__payment_method_id=payment_obj["id"])
        except PaymentMethod.DoesNotExist:
            pass
        else:
            payment_method_id = payment_method_obj.id
        return {
            "id": payment_method_id,
            "type": "bank_account",
            "payment_method_type": "ach_debit",
            "bank_name": payment_obj["us_bank_account"]["bank_name"],
            "last4": payment_obj["us_bank_account"]["last4"]
        }
    else:
        raise NotImplementedError("Only payment_type of card is supported")

def stripe_create_customer(**kwargs):
    merchant_id = kwargs.get("merchant_id", 0)
    unique_id = kwargs.get("unique_id", None)
    """
    {
        city: string,
        country: string,
        line1: string,
        line2: string,
        postal_code: string,
        state: string
    }
    """
    address = kwargs.get("address", None)
    email = kwargs.get("email", None)

    backend = "stripe"

    if unique_id == None:
        raise Exception("Please provide a unique id")
    if email == None:
        raise Exception("Please provide an email")

    email = email.lower()

    try:
        customer_obj = Customer.objects.get(merchant_id=merchant_id, unique_id=unique_id, customer_info__type=backend)
    except Customer.DoesNotExist:
        d_args = dict()
        if merchant_id > 0:
            try:
                merchant_obj = Merchant.objects.get(unique_id=merchant_id, provider=backend)
            except Merchant.DoesNotExist:
                return False, {"reason": "merchant_not_exist"}
            else:
                d_args['stripe_account'] = merchant_obj.merchant_info["account_id"]
        d_args['email'] = email
        if address != None:
            d_args['address'] = address
        response = _stripe_api_call(stripe.Customer.create, **d_args)
        if not response['is_success']:
            if response['resource']['code'] == "email_invalid":
                return False, {"reason": "email_invalid"}
        else:
            customer = response['resource']
            customer_obj = Customer(merchant_id=merchant_id, unique_id=unique_id)
            customer_obj.customer_info = {"type": backend, "customer_id": customer["id"]}
            customer_obj.save()
            return True, customer["address"]
    else:
        return False, {"reason": "customer_does_exist"}
    return False, {"reason": "unexpected_error"}

def stripe_get_customer_details(**kwargs):
    merchant_id = kwargs.get("merchant_id", 0)
    unique_id = kwargs.get("unique_id", None)
    
    try:
        customer_obj = Customer.objects.get(merchant_id=merchant_id, unique_id=unique_id)
    except Customer.DoesNotExist:
        return False, {"reason": "customer_doesnt_exist"}
    d_args = dict()
    d_args["id"] = customer_obj.customer_info["customer_id"]

    if merchant_id > 0:
        try:
            merchant_obj = Merchant.objects.get(unique_id=merchant_id, provider=backend)
        except Merchant.DoesNotExist:
            return False, {"reason": "merchant_not_exist"}
        else:
            d_args['stripe_account'] = merchant_obj.merchant_info["account_id"]

    response = _stripe_api_call(stripe.Customer.retrieve, **d_args)
    if not response['is_success']:
        return False, {"reason": "unexpected_error"}
    customer = response['resource']
    return True, {"address": customer["address"], "email": customer["email"]}

def stripe_create_payment_method(**kwargs):
    merchant_id = kwargs.get("merchant_id", 0)
    unique_id = kwargs.get("unique_id", None)
    off_session = kwargs.get("off_session", True)
    
    backend = "stripe"

    if unique_id == None:
        raise Exception("Please provide a unique id")

    if merchant_id != 0:
        raise NotImplementedError("Creating Customers on Merchants not supported")

    try:
        customer_obj = Customer.objects.get(merchant_id=merchant_id, unique_id=unique_id, customer_info__type=backend)
    except Customer.DoesNotExist:
        return False, {"reason": "customer_doesnt_exist"}

    if off_session:
        usage = "off_session"
    else:
        usage = "on_session"
    
    response = _stripe_api_call(stripe.SetupIntent.create, customer=customer_obj.customer_info["customer_id"], usage=usage)

    if not response['is_success']:
        return False, {"reason": "unexpected_error"}
    else:
        setup_intent = response['resource']
        return True, {"client_secret": setup_intent["client_secret"]}

def stripe_get_payment_method_detail(**kwargs):
    merchant_id = kwargs.get("merchant_id", 0)
    unique_id = kwargs.get("unique_id", 0)
    payment_method_id = kwargs.get("payment_method_id", False)
    payment_method_type = kwargs.get("payment_method_type", "payment_method")

    backend = "stripe"
    
    if payment_method_id == False:
        raise Exception("Please provide a payment_method_id")
    d_args = dict()
    d_args['id'] = payment_method_id
    if merchant_id > 0:
        try:
            merchant_obj = Merchant.objects.get(unique_id=merchant_id, provider=backend)
        except Merchant.DoesNotExist:
            return False, {"reason": "merchant_not_exist"}
        else:
            d_args['stripe_account'] = merchant_obj.merchant_info["account_id"]
    try:
        customer_obj = Customer.objects.get(merchant_id=merchant_id, unique_id=unique_id)
    except Customer.DoesNotExist:
        return False, {"reason": "customer_doesnt_exist"}
    if payment_method_type == "payment_method":
        response = _stripe_api_call(stripe.PaymentMethod.retrieve, **d_args)
    elif payment_method_type == "source":
        d_args['nested_id'] = d_args['id']
        d_args['id'] = customer_obj.customer_info["customer_id"]
        response = _stripe_api_call(stripe.Customer.retrieve_source, **d_args)
    if not response['is_success']:
        return False, {"reason": "unexpected_error"}
    return True, __stripe_payment_method_pretty(response['resource'])

def stripe_get_payment_method_details(**kwargs):
    merchant_id = kwargs.get("merchant_id", 0)
    unique_id = kwargs.get("unique_id", None)

    backend = "stripe"

    if unique_id == None:
        raise Exception("Please provide a unique id")

    try:
        customer_obj = Customer.objects.get(merchant_id=merchant_id, unique_id=unique_id)
    except Customer.DoesNotExist:
        return False, {"reason": "customer_doesnt_exist"}
    q_payment_method = PaymentMethod.objects.all().filter(merchant_id=merchant_id, unique_id=unique_id)
    l_pretty_payment_method = []
    for payment_method_obj in q_payment_method:
        is_success, pretty_payment_method = stripe_get_payment_method_detail(merchant_id=merchant_id, unique_id=unique_id, 
            payment_method_id=payment_method_obj.payment_method_info["payment_method_id"], 
            payment_method_type=payment_method_obj.payment_method_info["payment_method_type"])
        if not is_success:
            return False, {"reason": "unexpected_error"}
        l_pretty_payment_method.append(pretty_payment_method)

    return True, l_pretty_payment_method

def stripe_create_charge(**kwargs):
    merchant_id = kwargs.get("merchant_id", 0)
    unique_id = kwargs.get("unique_id", None)
    description = kwargs.get("description", None)
    amount = kwargs.get("amount", None) #This is the amount in cents
    auto_charge = kwargs.get("auto_charge", False)
    is_save_payment = kwargs.get("is_save_payment", False)
    payment_method_id = kwargs.get("payment_method_id", -1)
    metadata = kwargs.get("metadata", False)

    payment_token = None
    off_session = True
    backend = "stripe"

    if unique_id == None:
        raise Exception("Please provide a unique id")

    if amount == None:
        raise Exception("Please provide an charge amount")

    if description == None:
        raise Exception("Please provide a description")

    if amount <= 0:
        raise Exception("Please provide a valid charge amount(> 0)")

    if metadata != False and isinstance(metadata, dict) == False:
        raise Exception("Please provide a dictionary for the metadata")

    try:
        customer_obj = Customer.objects.get(merchant_id=merchant_id, unique_id=unique_id)
    except Customer.DoesNotExist:
        return False, {"reason": "customer_doesnt_exist"}
    d_args = dict()
    d_args['payment_method_types'] = ["card", "us_bank_account"]
    if merchant_id > 0:
        try:
            merchant_obj = Merchant.objects.get(unique_id=merchant_id, provider=backend)
        except Merchant.DoesNotExist:
            return False, {"reason": "merchant_not_exist"}
        else:
            d_args['stripe_account'] = merchant_obj.merchant_info["account_id"] 
    if auto_charge:
        q_payment_method = PaymentMethod.objects.all().filter(merchant_id=merchant_id, unique_id=unique_id, 
            payment_method_info__payment_method_type="payment_method")
        if payment_method_id == -1:
            for payment_method in q_payment_method:
                payment_token = payment_method.payment_method_info["payment_method_id"]
                break
        else:
            try:
                payment_method = q_payment_method.get(id=payment_method_id)
            except PaymentMethod.DoesNotExist:
                pass
            else:
                payment_token = payment_method.payment_method_info["payment_method_id"]
        if payment_token == None:
            return False, {"reason": "no_payment_method"}
        d_args['customer'] = customer_obj.customer_info["customer_id"]
        d_args['amount'] = int(amount)
        d_args['currency'] = "usd"
        d_args['confirm'] = True
        d_args['off_session'] = off_session
        d_args['payment_method'] = payment_token
        d_args['statement_descriptor'] = description
        if metadata != False:
            d_args['metadata'] = metadata
        response = _stripe_api_call(stripe.PaymentIntent.create, **d_args)
    else:
        d_args['customer'] = customer_obj.customer_info["customer_id"]
        d_args['amount'] = int(amount)
        d_args['currency'] = "usd"
        if is_save_payment:
            d_args['setup_future_usage'] = "off_session"
        d_args['statement_descriptor'] = description
        if metadata != False:
            d_args['metadata'] = metadata
        response = _stripe_api_call(stripe.PaymentIntent.create, **d_args)

    if not response['is_success']:
        return False, {"reason": "unexpected_error"}
    else:
        return True, {"client_secret": response['resource']['client_secret']}