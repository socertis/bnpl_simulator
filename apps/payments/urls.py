from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'plans', views.PaymentPlanViewSet, basename='paymentplan')

urlpatterns = [
    path('', include(router.urls)),
    path('installments/<int:installment_id>/pay/', views.pay_installment, name='pay_installment'),
    path('dashboard/stats/', views.dashboard_stats, name='dashboard_stats'),
    path('interest-rate/', views.get_interest_rate, name='get_interest_rate'),
]