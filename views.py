from django.shortcuts import render
from django.http import HttpResponse

# Create your views here.
def webhook_stripe(request):
    return HttpResponse("Stripe Webhook")

def webhook_stripe_return(request):
    return HttpResponse("Stripe Return Url")

def webhook_stripe_refresh(request):
    return HttpResponse("Stripe Refresh Url")