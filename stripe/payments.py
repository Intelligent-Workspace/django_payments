try:
    import stripe
except ImportError:
    raise Exception("Install the stripe SDK")

from django.conf import settings

from django_payments.models import Merchant, Customer, PaymentMethod
from django_payments.stripe.utils import _stripe_api_call

stripe.api_key = settings.PAYMENT_PRIVATE_KEY["stripe"]
stripe.max_network_retries = 2

def __stripe_payment_method_pretty(payment_obj, merchant_id, unique_id):
    if "card" in payment_obj:
        payment_method_id = -1
        try:
            payment_method_obj = PaymentMethod.objects.get(payment_method_info__payment_method_type="payment_method", 
                payment_method_info__payment_method_id=payment_obj["id"])
        except PaymentMethod.DoesNotExist:
            d_payment_method = {"payment_method_id": payment_obj["id"], "payment_method_type": "payment_method", "payment_method": "card"}
            payment_method_obj = PaymentMethod(merchant_id=merchant_id, unique_id=unique_id,
                payment_method_info=d_payment_method)
            payment_method_obj.save()
        
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
        payment_method_id = -1
        try:
            payment_method_obj = PaymentMethod.objects.get(payment_method_info__payment_method_type="payment_method", 
                payment_method_info__payment_method_id=payment_obj["id"])
        except PaymentMethod.DoesNotExist:
            d_payment_method = {"payment_method_id": payment_obj["id"], "payment_method_type": "payment_method", "payment_method": "ach_debit"}
            payment_method_obj = PaymentMethod(merchant_id=merchant_id, unique_id=unique_id,
                payment_method_info=d_payment_method)
            payment_method_obj.save()
        
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

    d_args = dict()
    if merchant_id > 0:
        try:
            merchant_obj = Merchant.objects.get(unique_id=merchant_id, provider=backend)
        except Merchant.DoesNotExist:
            return False, {"reason": "merchant_not_exist"}
        else:
            d_args['stripe_account'] = merchant_obj.merchant_info["account_id"]

    try:
        customer_obj = Customer.objects.get(merchant_id=merchant_id, unique_id=unique_id, customer_info__type=backend)
    except Customer.DoesNotExist:
        return False, {"reason": "customer_doesnt_exist"}

    if off_session:
        d_args['usage'] = "off_session"
    else:
        d_args['usage'] = "on_session"

    d_args['customer'] = customer_obj.customer_info["customer_id"]
    d_args['payment_method_types'] = ["card", "us_bank_account"]
    d_args['payment_method_options'] = {
        "us_bank_account": {
            "verification_method": "instant"
        }
    }
    
    response = _stripe_api_call(stripe.SetupIntent.create, **d_args)

    if not response['is_success']:
        return False, {"reason": "unexpected_error"}
    else:
        setup_intent = response['resource']
        return True, {"client_secret": setup_intent["client_secret"]}

def stripe_delete_payment_method(**kwargs):
    merchant_id = kwargs.get("merchant_id", 0)
    unique_id = kwargs.get("unique_id", None)
    payment_method_id = kwargs.get("payment_method_id", None)

    backend = "stripe"

    if unique_id == None:
        raise Exception("Please provide a unique id")
    
    if payment_method_id == None:
        raise Exception("Please provide a payment method id")
    
    try:
        customer_obj = Customer.objects.get(merchant_id=merchant_id, unique_id=unique_id)
    except Customer.DoesNotExist:
        return False, {"reason": "customer_doesnt_exist"}

    d_args = dict() 
    if merchant_id > 0:
        try:
            merchant_obj = Merchant.objects.get(unique_id=merchant_id, provider=backend)
        except Merchant.DoesNotExist:
            return False, {"reason": "merchant_not_exist"}
        else:
            d_args['stripe_account'] = merchant_obj.merchant_info["account_id"] 

    try:
        payment_method_obj = PaymentMethod.objects.get(merchant_id=merchant_id, unique_id=unique_id, id=payment_method_id)
    except PaymentMethod.DoesNotExist:
        return False, {"reason": "payment_method_doesnt_exist"}

    d_args['sid'] =  payment_method_obj.payment_method_info["payment_method_id"]
    response = _stripe_api_call(stripe.PaymentMethod.detach, **d_args)
    if response['is_success']:
        payment_method_obj.delete()
        return True, {}
    else:
        return False, {"reason": "unexpected_error"}

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
    return True, __stripe_payment_method_pretty(response['resource'], merchant_id, unique_id)

def stripe_get_payment_method_details(**kwargs):
    merchant_id = kwargs.get("merchant_id", 0)
    unique_id = kwargs.get("unique_id", None)
    payment_method_filter_list = kwargs.get("payment_method_filter_list", None)

    backend = "stripe"

    if unique_id == None:
        raise Exception("Please provide a unique id")

    try:
        customer_obj = Customer.objects.get(merchant_id=merchant_id, unique_id=unique_id)
    except Customer.DoesNotExist:
        return False, {"reason": "customer_doesnt_exist"}
    q_payment_method = PaymentMethod.objects.all().filter(merchant_id=merchant_id, unique_id=unique_id)
    if payment_method_filter_list is not None:
        q_payment_method = q_payment_method.filter(payment_method_info__payment_method__in=payment_method_filter_list)
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
    application_fee_amount = kwargs.get("application_fee_amount", 0) #This is the amount in cents
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

    if application_fee_amount < 0:
        raise Exception("Please provide a valid application fee amount(> 0)")

    if metadata != False and isinstance(metadata, dict) == False:
        raise Exception("Please provide a dictionary for the metadata")

    d_args = dict()
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
    d_args['payment_method_types'] = ["card", "us_bank_account"]
    d_args['payment_method_options'] = {
        "us_bank_account": {
            "verification_method": "instant"
        }
    }

    payment_token = None
    q_payment_method = PaymentMethod.objects.all().filter(merchant_id=merchant_id, unique_id=unique_id, 
        payment_method_info__payment_method_type="payment_method")
    if payment_method_id > -1:
        try:
            payment_method = q_payment_method.get(id=payment_method_id)
        except PaymentMethod.DoesNotExist:
            pass
        else:
            payment_token = payment_method.payment_method_info["payment_method_id"]

    if auto_charge:
        if payment_method_id == -1:
            for payment_method in q_payment_method:
                payment_token = payment_method.payment_method_info["payment_method_id"]
                break
        if payment_token == None:
            return False, {"reason": "no_payment_method"}
        d_args['customer'] = customer_obj.customer_info["customer_id"]
        d_args['amount'] = int(amount)
        d_args['application_fee_amount'] = application_fee_amount
        d_args['currency'] = "usd"
        d_args['confirm'] = True
        d_args['off_session'] = off_session
        d_args['statement_descriptor'] = description
        if metadata != False:
            d_args['metadata'] = metadata
    else:
        d_args['customer'] = customer_obj.customer_info["customer_id"]
        d_args['amount'] = int(amount)
        d_args['application_fee_amount'] = application_fee_amount
        d_args['currency'] = "usd"
        if is_save_payment:
            d_args['setup_future_usage'] = "off_session"
        d_args['statement_descriptor'] = description
        if metadata != False:
            d_args['metadata'] = metadata

    d_args['payment_method'] = payment_token
    response = _stripe_api_call(stripe.PaymentIntent.create, **d_args)

    if not response['is_success']:
        if response['resource']['code'] == "card_declined":
            if response['resource']['decline_code'] == "approve_with_id":
                return False, {"reason": "no_authorization"}
            elif response['resource']['decline_code'] == "card_not_supported":
                return False, {"reason": "card_not_supported"}
            elif response['resource']['decline_code'] == "currency_not_supported":
                return False, {"reason": "currency_not_supported"}
            elif response['resource']['decline_code'] == "duplicate_transaction":
                return False, {"reason": "duplicate_transaction"}
            elif response['resource']['decline_code'] == "expired_card":
                return False, {"reason": "expired_card"}
            elif (response['resource']['decline_code'] == "call_issuer" or
                  response['resource']['decline_code'] == "do_not_honor" or
                  response['resource']['decline_code'] == "do_not_try_again" or
                  response['resource']['decline_code'] == "fraudulent" or
                  response['resource']['decline_code'] == "generic_decline" or
                  response['resource']['decline_code'] == "invalid_account" or
                  response['resource']['decline_code'] == "invalid_amount" or
                  response['resource']['decline_code'] == "issuer_not_available" or
                  response['resource']['decline_code'] == "lost_card" or
                  response['resource']['decline_code'] == "merchant_blacklist" or
                  response['resource']['decline_code'] == "new_account_information_available" or
                  response['resource']['decline_code'] == "no_action_taken" or
                  response['resource']['decline_code'] == "not_permitted" or
                  response['resource']['decline_code'] == "offline_pin_required" or
                  response['resource']['decline_code'] == "online_or_offline_pin_required" or
                  response['resource']['decline_code'] == "pickup_card" or
                  response['resource']['decline_code'] == "pin_try_exceeded" or
                  response['resource']['decline_code'] == "reenter_transaction" or
                  response['resource']['decline_code'] == "restriction_card" or
                  response['resource']['decline_code'] == "revocation_of_all_authorizations" or
                  response['resource']['decline_code'] == "revocation_of_authorization" or
                  response['resource']['decline_code'] == "security_violation" or
                  response['resource']['decline_code'] == "service_not_allowed" or
                  response['resource']['decline_code'] == "stolen_card" or
                  response['resource']['decline_code'] == "stop_payment_order" or
                  response['resource']['decline_code'] == "testmode_decline" or
                  response['resource']['decline_code'] == "transaction_not_allowed" or
                  response['resource']['decline_code'] == "try_again_later" or
                  response['resource']['decline_code'] == "authentication_required"):
                  return False, {"reason": "generic_decline"}
            elif (response['resource']['decline_code'] == "incorrect_number" or 
                  response['resource']['decline_code'] == "incorrect_cvc" or 
                  response['resource']['decline_code'] == "incorrect_pin" or
                  response['resource']['decline_code'] == "incorrect_zip" or
                  response['resource']['decline_code'] == "invalid_cvc" or
                  response['resource']['decline_code'] == "invalid_expiry_month" or
                  response['resource']['decline_code'] == "invalid_expiry_year" or
                  response['resource']['decline_code'] == "invalid_number" or
                  response['resource']['decline_code'] == "invalid_pin"):
                  return False, {"reason": "incorrect_card_info"}
            elif (response['resource']['decline_code'] == "insufficient_funds" or
                  response['resource']['decline_code'] == "card_velocity_exceeded" or
                  response['resource']['decline_code'] == "withdrawal_count_limit_exceeded"):
                  return False, {"reason": "limit_exceeded"}
            elif response['resource']['decline_code'] == "processing_error":
                return False, {"reason": "processing_error"}
        elif response['resource']['code'] == "expired_card":
            return False, {"reason": "expired_card"}
        elif response['resource']['code'] == "processing_error":
            return False, {"reason": "processing_error"}
        return False, {"reason": "unexpected_error"}
    else:
        return True, {"client_secret": response['resource']['client_secret']}

def stripe_update_charge(**kwargs):
    merchant_id = kwargs.get("merchant_id", 0)
    unique_id = kwargs.get("unique_id", None)
    payment_intent_id = kwargs.get("payment_intent_id", None)
    is_save_payment = kwargs.get("is_save_payment", False)
    
    backend = "stripe"
    
    if unique_id == None:
        raise Exception("Please provide a unique id")

    if payment_intent_id == None:
        raise Exception("Please provide a payment intent id")

    d_args = dict()
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

    d_args["sid"] = payment_intent_id
    if is_save_payment:
        d_args['setup_future_usage'] = "off_session"
    else:
        d_args['setup_future_usage'] = ""
    response = _stripe_api_call(stripe.PaymentIntent.modify, **d_args)