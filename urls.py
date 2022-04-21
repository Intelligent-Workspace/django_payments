from django.urls import path

from . import views

app_name = "django_payments"
urlpatterns = [
    path('webhook_stripe/', views.webhook_stripe, name="webhook_stripe"),
]