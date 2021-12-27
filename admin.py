from django.contrib import admin
from django_payments.models import Merchant, Customer, PaymentMethod

# Register your models here.
admin.site.register(Merchant)
admin.site.register(Customer)
admin.site.register(PaymentMethod)