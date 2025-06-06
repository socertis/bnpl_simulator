from django.urls import path
from . import views

urlpatterns = [
    path('merchant/', views.merchant_analytics, name='merchant_analytics'),
    path('trends/', views.payment_trends, name='payment_trends'),
]