# DjangoPayments

### Announcements

#### Disclaimer

This library is currently under active development and the API's are subject to without any notice or backwards compatibility

## Welcome to DjangoPayments, Intelligent Workspace's Backend Payments Library

### Getting Started

1. Clone the Repository

   ```
   git clone git@github.com:Intelligent-Workspace/django_payments.git 
   														OR
   git clone https://github.com/Intelligent-Workspace/django_payments.git
   
   Please refer to the Directory Diagram Below to figure out where to clone the repo in your Django Project
   ```

   ```
   |	+-- my-project
   
   |			+-- my-project
   
   |					+-- asgi.py
   
   |					+-- settings.py
   
   |					+-- urls.py
   
   |					+-- wsgi.py
   
   |			+-- manage.py
   
   |			+-- django_payments
   ```

2. Change your settings.py file

   ```python
   ...
   
   INSTALLED_APPS = [
     "...",
     "django_payments",
     "..."
   ]
   
   #Available Payment Backend: "stripe"
   
   PAYMENT_BACKEND = "<your primary payment backend>"
   PAYMENT_PRIVATE_KEY = {
     "<backend>": "<api key of backend>"
   }
   PAYMENT_MISC_SETTINGS = {
     "stripe": {
       "refresh_url": "<reverse formatted string pointing to a view>",
       "return_url": "<reverse formatted string pointing to a view>",
       "webhook_signing_secret": "<secret which stripe webhook events are signed with>"
     }
   }
   
   """
   Additional Information:
   	1. Stripe
   		a. MISC_SETTINGS -> refresh_url - This is the view that gets called when something goes wrong with the current merchant onboarding session
   		b. MISC_SETTINGS -> return_url - This is the view that gets called when the merchant onboarding session is gracefully exited. This doesn't necessarily mean that the onboarding is completed
   """
   
   ...
   ```

3. Now you should be able to use DjangoPayment in your application!



### API Reference

```python
merchant.py

"""
To use functions from this file, use django_payments.merchant to import specific functions

ex: from django_payments.merchant import merchant_create
"""


def merchant_create(**kwargs):
  ...
  
  """
  Use this function to create a merchant or retrieve onboarding information for an existing merchant
  
  Parameters:
  	backend - Defaults to the value of settings.PAYMENT_BACKEND (currently the only supported value is "stripe")
  	unique_id - This is an int used to uniquely identify each merchant.
  	country - The country of origin this merchant is operating in (currently the only supported value is "us")
  	base_url - This is the your full url of your server without a trailing / (ex. https://www.test.com)
  	
  Returns:
  	tuple() -> (is_success, response_or_error)
  	IF request is successfully processed:
  		is_success is True
  		response_or_error contains the url the user needs to be redirected to for merchant onboarding
  	IF request is not successfully processed:
  		is_success is False
  		response_or_error is a dictionary which contains one key: "reason"
  		Possible Values for "reason":
  			1. unexpected_error - There was an unexpected error. Please try this request again
  			
  Backend Specific Information:
  	1. Stripe
  		a. This function creates a standard account with Stripe Connect APIs
  """
  
def merchant_sync(**kwargs):
  ...
  
  """
  Use this function to manually sync the state of an existing merchant from the backend provider. This should only be used in extreme cases when the SDK doesn't automatically handle merchant state updates.
  
  Parameters:
  	backend - Defaults to the value of settings.PAYMENT_BACKEND (currently the only supported value is "stripe")
  	unique_id - This is an int used to uniquely identify each merchant
  	
  Returns:
  	tuple() -> (is_success, response_or_error)
  	IF request is successfully processed:
  		is_success is True
  		response_or_error is an empty dictionary
  	IF request is not successfully processed:
  		is_success is False
  		response_or_error is a dictionary which contains one key: "reason"
  		Possible Values for "reason":
  			1. "merchant_not_exist" - The merchant specificied with the unique_id doesn't exist. This is an invalid request
  			2. "unexpected_error" - There was an unexpected error. Please try this request again.
  """
  
def merchant_state(**kwargs):
  ...
  
  """
  Use this function to determine the step of the onboard process the merchant is on
  
  Parameters:
  	backend - Defaults to the value of settings.PAYMENT_BACKEND (currently the only supported value is "stripe")
  	unique_id - This is an int used to uniquely identify each merchant
  	
  Returns:
  	tuple() -> (is_success, response_or_error)
  	IF request is successfully processed:
  		is_success is True
  		response_or_error is a dictionary which contains one key: "status"
  		Possible Values for "status":
  			1. "setup_not_started" - The Merchant Onboarding for this merchant hasn't been started. This could mean that no merchant is created with the specified unique_id
  			2. "setup_started" - The Merchant Onboarding for this merchant has been started but has not been completed yet
  			3. "setup_finished" - The Merchant Onboarding for this merchant has been completed
  """
```



```python
payments.py

"""
To use functions from this file, use django_payments.payments to import specific functions

ex: from django_payments.payments import merchant_create
"""


def create_customer(**kwargs):
  ...
  
  """
  Use this function to create a billable customer
  
  Interfaces:
  	address: {
  		line1: string,
  		line2: string,
  		city: string,
  		postal_code: string,
  		state: string,
  		country: string
  	}
  
  Parameters:
  	backend - Defaults to the value of settings.PAYMENT_BACKEND (currently the only supported value is "stripe")
  	email - This is a string representing the email of this customer
  	unique_id - This is an int to uniquely identify each customer
  	merchant_id - This is an int to uniquely identify each merchant. Pass a value to this parameter if you wish to create a customer under this merchant [OPTIONAL]
  	address - This is a dictionary of structure INTERFACE address. Pass a value to this parameter if you wish to store a billing address for this customer [OPTIONAL]
  	
  Returns:
  	tuple() -> (is_success, response_or_error)
  	IF request is successfully processed:
  		is_success is True
  		response_or_error is a dictionary of structure INTERFACE address
  	IF request is not successfully processed:
  		is_success is False
  		response_or_error is a dictionary which contains one key: "reason"
  		Possible Values for "reason":
  			1. "merchant_not_exist" - If a merchant_id is provided, then the merchant doesn't exist
  			2. "email_invalid" - The format of the email is invalid
  			3. "customer_does_exist" - This is already a customer which exists with the given unique_id
  			4. "unexpected_error" - There was an unexpected error. Please try this request again.
  """
  
 def get_customer_details(**kwargs):
  ...
  
  """
  Use this function to get information about a billable customer
  
  Interfaces:
  	address: {
  		line1: string | None,
  		line2: string | None,
  		city: string | None,
  		postal_code: string | None,
  		state: string | None,
  		country: string | None
  	}
  	
  Parameters:
  	backend - Defaults to the value of settings.PAYMENT_BACKEND (currently the only supported value is "stripe")
  	unique_id - This is an int to uniquely identify each customer
  	merchant_id - This is an int to uniquely identify each merchant. Pass a value to this parameter if you wish to fetch a customer under this merchant [OPTIONAL]
  	
  Returns:
  	tuple() -> (is_success, response_or_error)
  	IF request is successfully processed:
  		is_success is True
  		response_or_error is a dictionary which contains two keys: "address" and "email"
  		Possible Values for "address":
  			1. A dictionary of structure INTERFACE address
  		Possible Values for "email":
  			1. A string formatted like an email
  	IF request is not successfully processed:
  		is_success is False
  		response_or_error is a dictionary which contains one key: "reason"
  		Possible Values for "reason":
  			1. "customer_doesnt_exist" - The customer with the given unique_id doesn't exist
  			2. "merchant_not_exist" - If a merchant_id is provided, then the merchant doesn't exist
  			3. "unexpected_error" - There was an unexpected error. Please try this request again.
  """
  
 def create_payment_method(**kwargs):
  ...
  
  """
  Use this function to create a payment_method
  
  Parameters:
  	backend - Defaults to the value of settings.PAYMENT_BACKEND (currently the only supported value is "stripe")
  	unique_id - This is an int to uniquely identify each customer
  	off_session - This is a boolean representing whether the customer will be present when you charge this payment_method. Default value is True [OPTIONAL]
  	
  Returns:
  	tuple() -> (is_success, response_or_error)
  	IF request is successfully processed:
  		is_success is True
  		response_or_error is a dictionary which contains one key: "client_secret"
  		Possible Values for "client_secret":
  			1. A string represented a client_secret which can be used on the frontend to complete adding the payment_method.
  				 Each backend has their own way of dealing with payment_methods in the frontend:
  				 Relevant Documentation per backend:
  				 	1. Stripe - https://stripe.com/docs/js/setup_intents/confirm_card_setup (Currently only card payment_methods can be attached)
  	IF request is not successfully processed:
  		is_success is False
  		response_or_error is a dictionary which contains one key: "reason"
  		Possible Values for "reason":
  			1. "customer_doesnt_exist" - The customer with the given unique_id doesn't exist
  			2. "unexpected_error" - There was an unexpected error. Please try this request again.
  """
  
def get_payment_method_details(**kwargs):
  ...
  
  """
  Use this function to get the details of all the payment_methods stored for a billable customer
  
  Interfaces:
  	payment_method: {
  		type: string
  	}
  	card_method extends payment_method: {
  		type: "card",
  		brand: string,
  		last4: string,
  		exp_month: number,
  		exp_year: number
  	}
  
  Parameters:
  	backend - Defaults to the value of settings.PAYMENT_BACKEND (currently the only supported value is "stripe")
  	unique_id - This is an int to uniquely identify each customer
    
  Returns:
  	tuple() -> (is_success, response_or_error)
  	IF request is successfully processed:
  		is_success is True
  		response_or_error is a list of dictionaries of INTERFACE payment_method
  	IF request is not successfully processed:
  		is_success is False
  		response_or_error is a dictionary which contains one key: "reason"
  		Possible Values for "reason":
  			1. "customer_doesnt_exist" - The customer with the given unique_id doesn't exist
  			2. "unexpected_error" - There was an unexpected error. Please try this request again.
  """
  
def create_charge(**kwargs):
  ...
  
  """
  Use this function to charge a billable customer
  
  Parameters:
  	backend - Defaults to the value of settings.PAYMENT_BACKEND (currently the only supported value is "stripe")
  	unique_id - This is an int to uniquely identify each customer
  	description - This is a string which describes the charge
  	amount - This is an int which represented the amount charged in cents
  	merchant_id - This is an int to uniquely identify each merchant. Pass a value to this parameter if you wish to create a charge for a customer under this merchant [OPTIONAL]
  	auto_charge - This is a boolean which represents if the charge should be captured with avaliable payment_methods for this customer. Currently, you cannot auto_charge for a customer under a merchant. Default value is True [OPTIONAL]
  	off_session - This is a boolean representing whether the customer will be present when you charge this payment_method. Default value is True [OPTIONAL]
  	
  Returns:
  	tuple() -> (is_success, response_or_error)
  	IF request is successfully processed:
  		is_success is True
  		response_or_error is a dictionary which contains one key: "client_secret"
  		Possible Values for "client_secret":
  			1. A string represented a client_secret which can be used on the frontend to complete adding the payment_method.
  				 Each backend has their own way of dealing with payment_methods in the frontend:
  				 Relevant Documentation per backend:
  				 	1. Stripe - https://stripe.com/docs/js/payment_intents/confirm_card_payment (Currently only card payment_methods can be attached)
  	IF request is not successfully processed:
  		is_success is False
  		response_or_error is a dictionary which contains one key: "reason"
  		Possible Values for "reason":
  			1. "customer_doesnt_exist" - The customer with the given unique_id doesn't exist
  			2. "merchant_not_exist" - If a merchant_id is provided, then the merchant doesn't exist
  			3. "unexpected_error" - There was an unexpected error. Please try this request again.
  """
```

