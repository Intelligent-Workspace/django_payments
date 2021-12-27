from django.urls import path

from . import views

app_name = "django_payments"
urlpatterns = [
    path('webhook_stripe/', views.webhook_stripe, name="webhook_stripe"),
    path('webhook_stripe_refresh/', views.webhook_stripe_refresh, name="webhook_stripe_refresh"),
    path('webhook_stripe_return/', views.webhook_stripe_return, name="webhook_stripe_return")
]