try:
    import stripe
except ImportError:
    raise Exception("Install the stripe SDK")

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
        if e.code == "card_declined":
            d_resource['decline_code'] = e.json_body['error']['decline_code']
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