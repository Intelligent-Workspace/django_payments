try:
    import stripe
except ImportError:
    raise Exception("Install the stripe SDK")

from django.conf import settings

from django_payments.models import Merchant, Customer, PaymentMethod

stripe.api_key = settings.PAYMENT_PRIVATE_KEY
stripe.max_network_retries = 2

def __stripe_payment_method_pretty(payment_obj):
    if "card" in payment_obj:
        return {
            "type": "card",
            "brand": payment_obj["card"]["brand"],
            "last4": payment_obj["card"]["last4"],
            "cvc_verify": True,
            "zip_verify": True,
            "exp_month": payment_obj["card"]["exp_month"],
            "exp_year": payment_obj["card"]["exp_year"]
        }
    else:
        raise NotImplementedError("Only payment_type of card is supported")

def _stripe_api_call(stripe_func, **kwargs):
    try:
        return_value = stripe_func(**kwargs)
    except stripe.error.CardError as e:
        d_resource = {
            "status": e.http_status,
            "code": e.code,
            "param": e.param,
            "message": e.user_message
        }
        return {"is_success": False, "resource": d_resource}
    except stripe.error.RateLimitError as e:
        d_resource = {
            "status": e.http_status,
            "code": e.code,
            "message": e.user_message
        }
        return {"is_success": False, "resource": d_resource}
    except stripe.error.InvalidRequestError as e:
        d_resource = {
            "status": e.http_status,
            "code": e.code,
            "param": e.param,
            "message": e.user_message
        }
        return {"is_success": False, "resource": d_resource}
    except stripe.error.AuthenticationError as e:
        d_resource = {
            "status": e.http_status,
            "code": e.code,
            "message": e.user_message
        }
        return {"is_success": False, "resource": d_resource}
    except stripe.error.APIConnectionError as e:
        d_resource = {
            "status": e.http_status,
            "code": e.code,
            "message": e.user_message
        }
        return {"is_success": False, "resouce": d_resource}
    except stripe.error.StripeError as e:
        d_resource = {
            "status": e.http_status,
            "code": e.code,
            "message": e.user_message
        }
        return {"is_success": False, "resource": d_resource}
    except Exception as e:
        return {"is_success": False, "resource": "unexpected_error"}
    else:
        return {"is_success": True, "resource": return_value}

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
    if address == None:
        raise Exception("Please provide an address")
    if email == None:
        raise Exception("Please provide an email")

    if merchant_id != 0:
        raise NotImplementedError("Creating Customers on Merchants not supported")

    try:
        customer_obj = Customer.objects.get(merchant_id=merchant_id, unique_id=unique_id, customer_info__type=backend)
    except Customer.DoesNotExist:
        response = _stripe_api_call(stripe.Customer.create, address=address, email=email)
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

def stripe_get_customer_details(**kwargs):
    merchant_id = kwargs.get("merchant_id", 0)
    unique_id = kwargs.get("unique_id", None)
    
    if merchant_id != 0:
        raise NotImplementedError("Creating Customers on Merchants not supported")

    try:
        customer_obj = Customer.objects.get(merchant_id=merchant_id, unique_id=unique_id)
    except Customer.DoesNotExist:
        return False, {"reason": "customer_doesnt_exist"}
    customer = stripe.Customer.retrieve(customer_obj.customer_info["customer_id"])
    return True, {"address": customer["address"]}

def stripe_create_payment_method(**kwargs):
    merchant_id = kwargs.get("merchant_id", 0)
    unique_id = kwargs.get("unique_id", None)
    payment_type = kwargs.get("payment_type", None)
    off_session = kwargs.get("off_session", True)
    
    backend = "stripe"

    if unique_id == None:
        raise Exception("Please provide a unique id")
    if payment_type == None:
        raise Exception("Please provide a payment type")

    if payment_type != "card":
        raise NotImplementedError("Only payment_type of card is supported")
    
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
        return True, {"type": payment_type, "client_secret": setup_intent["client_secret"]}

def stripe_get_payment_method_details(**kwargs):
    merchant_id = kwargs.get("merchant_id", 0)
    unique_id = kwargs.get("unique_id", None)

    backend = "stripe"

    if unique_id == None:
        raise Exception("Please provide a unique id")

    if merchant_id != 0:
        raise NotImplementedError("Creating Customers on Merchants not supported")

    try:
        customer_obj = Customer.objects.get(merchant_id=merchant_id, unique_id=unique_id)
    except Customer.DoesNotExist:
        return False, {"reason": "customer_doesnt_exist"}
    q_payment_method = PaymentMethod.objects.all().filter(merchant_id=merchant_id, unique_id=unique_id)
    l_pretty_payment_method = []
    for payment_method_obj in q_payment_method:
        response = _stripe_api_call(stripe.PaymentMethod.retrieve, id=payment_method_obj.payment_method_info["payment_method_id"])
        if not response['is_success']:
            return False, {"reason": "unexpected_error"}
        payment_method = response['resource']
        l_pretty_payment_method.append(__stripe_payment_method_pretty(payment_method))

    return True, l_pretty_payment_method

def stripe_create_charge(**kwargs):
    merchant_id = kwargs.get("merchant_id", 0)
    unique_id = kwargs.get("unique_id", None)
    description = kwargs.get("description", None)
    amount = kwargs.get("amount", None) #This is the amount in cents
    payment_token = kwargs.get("payment_token", None)

    backend = "stripe"

    if unique_id == None:
        raise Exception("Please provide a unique id")

    if amount == None:
        raise Exception("Please provide an charge amount")

    if description == None:
        raise Exception("Please provide a description")

    if amount <= 0:
        raise Exception("Please provide a valid charge amount(> 0)")

    if merchant_id != 0:
        raise NotImplementedError("Creating Charges on Merchants not supported")

    try:
        customer_obj = Customer.objects.get(merchant_id=merchant_id, unique_id=unique_id)
    except Customer.DoesNotExist:
        return False, {"reason": "customer_doesnt_exist"}
    if payment_token == None:
        q_payment_method = PaymentMethod.objects.all().filter(merchant_id=merchant_id, unique_id=unique_id)
        if q_payment_method.count() == 0:
            raise Exception("Please add a payment method for this customer before charging or provide a payment token")
        for payment_method in q_payment_method:
            payment_token = payment_method.payment_method_info["payment_method_id"]
            break
        if payment_token == None:
            raise Exception("Please make sure this customer has atleast one confirmed payment method registered")
    """
    charge = stripe.Charge.create(customer=customer_obj.customer_info["customer_id"], amount=int(amount), currency="usd",
        source=payment_token, description=description)
    """
    try:
        payment_intent = stripe.PaymentIntent.create(
            customer=customer_obj.customer_info["customer_id"],
            amount=int(amount), currency="usd", confirm=True, off_session=True,
            payment_method=payment_token, statement_descriptor=description
        )
    except stripe.error.CardError as e:
        print(e)

    return True, {}