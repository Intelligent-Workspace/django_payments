try:
    import stripe
except ImportError:
    raise Exception("Install the stripe SDK")

from django.conf import settings

from django_payments.models import Merchant, Customer, PaymentMethod
from django_payments.stripe.utils import _stripe_api_call

stripe.api_key = settings.PAYMENT_PRIVATE_KEY["stripe"]
stripe.max_network_retries = 2

if settings.PAYMENT_MISC_SETTINGS["stripe"].get("ach_auth", None) != None:
    if settings.PAYMENT_MISC_SETTINGS["stripe"]['ach_auth']['provider'] == "plaid":
        try:
            import plaid
            from plaid.api import plaid_api
        except ImportError:
            raise Exception("Install the plaid SDK")
        if settings.PAYMENT_MISC_SETTINGS["stripe"]['ach_auth']['is_sandbox']:
            plaid_host_type = plaid.Environment.Sandbox
        else:
            plaid_host_type = plaid.Environment.Production
        plaid_configuration = plaid.Configuration(
            host=plaid_host_type,
            api_key={
                'clientId': settings.PAYMENT_MISC_SETTINGS["stripe"]['ach_auth']['client_id'],
                'secret': settings.PAYMENT_MISC_SETTINGS["stripe"]['ach_auth']['secret']
            }
        )
        plaid_api_client = plaid.ApiClient(plaid_configuration)
        plaid_client = plaid_api.PlaidApi(plaid_api_client)

def __stripe_payment_method_pretty(payment_obj):
    if "card" in payment_obj:
        return {
            "type": "card",
            "brand": payment_obj["card"]["brand"],
            "last4": payment_obj["card"]["last4"],
            "exp_month": payment_obj["card"]["exp_month"],
            "exp_year": payment_obj["card"]["exp_year"]
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
    payment_method_id = kwargs.get("payment_method_id", False)

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
    response = _stripe_api_call(stripe.PaymentMethod.retrieve, **d_args)
    if not response['is_success']:
        return False, {"reason": "unexpected_error"}
    return True, __stripe_payment_method_pretty(response['resource'])

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
        is_success, pretty_payment_method = stripe_get_payment_method_detail(merchant_id=merchant_id, unique_id=unique_id, 
            payment_method_id=payment_method_obj.payment_method_info["payment_method_id"])
        if not is_success:
            return False, {"reason": "unexpected_error"}
        l_pretty_payment_method.append(pretty_payment_method)

    return True, l_pretty_payment_method

def stripe_create_charge(**kwargs):
    merchant_id = kwargs.get("merchant_id", 0)
    unique_id = kwargs.get("unique_id", None)
    description = kwargs.get("description", None)
    amount = kwargs.get("amount", None) #This is the amount in cents
    off_session = kwargs.get("off_session", True)
    auto_charge = kwargs.get("auto_charge", False)
    metadata = kwargs.get("metadata", False)

    payment_token = None
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
    if auto_charge:
        if merchant_id != 0:
            raise NotImplementedError("Creating Auto Charges on Merchants not supported")
        q_payment_method = PaymentMethod.objects.all().filter(merchant_id=merchant_id, unique_id=unique_id)
        for payment_method in q_payment_method:
            payment_token = payment_method.payment_method_info["payment_method_id"]
            break
        if payment_token == None:
            return False, {"reason": "no_payment_method"}
        if metadata != False:
            response = _stripe_api_call(stripe.PaymentIntent.create, customer=customer_obj.customer_info["customer_id"], amount=int(amount),
                currency="usd", confirm=True, off_session=off_session, payment_method=payment_token, statement_descriptor=description, metadata=metadata)
        else:
            response = _stripe_api_call(stripe.PaymentIntent.create, customer=customer_obj.customer_info["customer_id"], amount=int(amount),
                currency="usd", confirm=True, off_session=off_session, payment_method=payment_token, statement_descriptor=description)
    else:
        d_args = dict()
        if merchant_id > 0:
            try:
                merchant_obj = Merchant.objects.get(unique_id=merchant_id, provider=backend)
            except Merchant.DoesNotExist:
                return False, {"reason": "merchant_not_exist"}
            else:
                d_args['stripe_account'] = merchant_obj.merchant_info["account_id"]
        d_args['customer'] = customer_obj.customer_info["customer_id"]
        d_args['amount'] = int(amount)
        d_args['currency'] = "usd"
        #d_args['off_session'] = off_session
        d_args['statement_descriptor'] = description
        if metadata != False:
            d_args['metadata'] = metadata
        response = _stripe_api_call(stripe.PaymentIntent.create, **d_args)

    if not response['is_success']:
        return False, {"reason": "unexpected_error"}
    else:
        return True, {"client_secret": response['resource']['client_secret']}

def stripe_ach_create_auth_token(**kwargs):
    merchant_id = kwargs.get("merchant_id", 0)
    unique_id = kwargs.get("unique_id", None)
    application_name = settings.PAYMENT_MISC_SETTINGS["stripe"]['ach_auth']['application_name']

    if unique_id == None:
        raise Exception("Please provide a unique id")
    if application_name == None:
        raise Exception("Please provide an application name")

    try:
        customer_obj = Customer.objects.get(merchant_id=merchant_id, unique_id=unique_id)
    except Customer.DoesNotExist:
        return False, {"reason": "customer_doesnt_exist"}

    from plaid.model.link_token_create_request import LinkTokenCreateRequest
    from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
    from plaid.model.products import Products
    from plaid.model.country_code import CountryCode

    request = LinkTokenCreateRequest(
        products=[Products("auth")],
        client_name=application_name,
        country_codes=[CountryCode('US')],
        language="en",
        user=LinkTokenCreateRequestUser(
            client_user_id=str(unique_id)
        )
    )

    response = plaid_client.link_token_create(request)
    return True, {"token": response['link_token']}

def stripe_ach_swap_public_token_backend_token(**kwargs):
    merchant_id = kwargs.get("merchant_id", 0)
    unique_id = kwargs.get("unique_id", None)
    public_token = kwargs.get("public_token", None)
    account_id = kwargs.get("account_id", None)

    if unique_id == None:
        raise Exception("Please provide a unique id")
    if public_token == None:
        raise Exception("Please provide a public token")
    if account_id == None:
        raise Exception("Please provide a account id")

    try:
        customer_obj = Customer.objects.get(merchant_id=merchant_id, unique_id=unique_id)
    except Customer.DoesNotExist:
        return False, {"reason": "customer_doesnt_exist"}
    
    from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
    from plaid.model.processor_stripe_bank_account_token_create_request import ProcessorStripeBankAccountTokenCreateRequest

    exchange_request = ItemPublicTokenExchangeRequest(public_token=public_token)
    exchange_token_response = plaid_client.item_public_token_exchange(exchange_request)
    access_token = exchange_token_response['access_token']

    processor_exchange_request = ProcessorStripeBankAccountTokenCreateRequest(
        access_token=access_token,
        account_id=account_id,
    )
    
    stripe_response = plaid_client.processor_stripe_bank_account_token_create(processor_exchange_request)
    return True, {"backend_token": stripe_response['stripe_bank_account_token']}

def stripe_ach_create_charge(**kwargs):
    merchant_id = kwargs.get("merchant_id", 0)
    unique_id = kwargs.get("unique_id", None)
    backend_token = kwargs.get("backend_token", None)
    description = kwargs.get("description", None)
    amount = kwargs.get("amount", None) #This is the amount in cents
    metadata = kwargs.get("metadata", False)

    backend = "stripe"

    if unique_id == None:
        raise Exception("Please provide a unique id")

    if amount == None:
        raise Exception("Please provide an charge amount")

    if description == None:
        raise Exception("Please provide a description")

    if amount <= 0:
        raise Exception("Please provide a valid charge amount(> 0)")

    try:
        customer_obj = Customer.objects.get(merchant_id=merchant_id, unique_id=unique_id)
    except Customer.DoesNotExist:
        return False, {"reason": "customer_doesnt_exist"}

    d_args = dict()
    d_args['customer'] = customer_obj.customer_info["customer_id"]
    d_args['amount'] = int(amount)
    d_args['currency'] = "usd"
    d_args['statement_descriptor'] = description
    if metadata != False:
        d_args['metadata'] = metadata
    if merchant_id > 0:
        try:
            merchant_obj = Merchant.objects.get(unique_id=merchant_id, provider=backend)
        except Merchant.DoesNotExist:
            return False, {"reason": "merchant_not_exist"}
        else:
            d_args['stripe_account'] = merchant_obj.merchant_info["account_id"]

    if d_args.get("stripe_account", None) == None:
        source_response = _stripe_api_call(stripe.Customer.create_source, id=d_args['customer'], source=backend_token)
    else:
        source_response = _stripe_api_call(stripe.Customer.create_source, stripe_account=d_args['stripe_account'], id=d_args['customer'], 
            source=backend_token)
    d_args['source'] = source_response['resource']['id']
    response = _stripe_api_call(stripe.Charge.create, **d_args)
    if d_args.get("stripe_account", None) == None:
        source_response = _stripe_api_call(stripe.Customer.delete_source, id=d_args['customer'], nested_id=d_args['source'])
    else:
        source_response = _stripe_api_call(stripe.Customer.delete_source, stripe_account=d_args['stripe_account'], id=d_args['customer'], 
            nested_id=d_args['source'])
    if response['is_success']:
        return True, {}
    else:
        if response['resource']['code'] == "amount_too_large":
            return False, {"reason": "amt_too_large"}
        elif response['resource']['code'] == "amount_too_small":
            return False, {"reason": "amt_too_small"}
        elif response['resource']['code'] == "bank_account_unusable":
            return False, {"reason": "bank_acc_not_usable"}
        elif response['resource']['code'] == "debit_not_authorized":
            return False, {"reason": "unauthorized_payment"}
        elif response['resource']['code'] == "insufficient_funds":
            return False, {"reason": "insufficient_funds"}
        return False, {}