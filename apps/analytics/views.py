from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import permissions
from django.db.models import Sum, Count, Q
from apps.payments.models import PaymentPlan, Installment
from apps.authentication.permissions import IsMerchant
from datetime import date, timedelta

@api_view(['GET'])
@permission_classes([IsMerchant])
def merchant_analytics(request):
    """
    Get comprehensive analytics for merchants
    """
    merchant = request.user
    plans = PaymentPlan.objects.filter(merchant=merchant)
    
    # Basic metrics
    total_plans = plans.count()
    active_plans = plans.filter(status='active').count()
    completed_plans = plans.filter(status='completed').count()
    
    # Revenue metrics
    total_revenue = plans.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    completed_revenue = plans.filter(status='completed').aggregate(
        Sum('total_amount')
    )['total_amount__sum'] or 0
    
    # Installment metrics
    all_installments = Installment.objects.filter(payment_plan__merchant=merchant)
    paid_installments = all_installments.filter(status='paid').count()
    pending_installments = all_installments.filter(status='pending').count()
    late_installments = all_installments.filter(status='late').count()
    
    # Success rate
    success_rate = (completed_plans / total_plans * 100) if total_plans > 0 else 0
    
    # Recent activity (last 30 days)
    thirty_days_ago = date.today() - timedelta(days=30)
    recent_plans = plans.filter(created_at__gte=thirty_days_ago).count()
    recent_payments = all_installments.filter(
        paid_date__gte=thirty_days_ago,
        status='paid'
    ).count()
    
    return Response({
        'overview': {
            'total_plans': total_plans,
            'active_plans': active_plans,
            'completed_plans': completed_plans,
            'success_rate': round(success_rate, 2),
        },
        'revenue': {
            'total_revenue': float(total_revenue),
            'completed_revenue': float(completed_revenue),
            'pending_revenue': float(total_revenue - completed_revenue),
        },
        'installments': {
            'total_installments': all_installments.count(),
            'paid_installments': paid_installments,
            'pending_installments': pending_installments,
            'late_installments': late_installments,
        },
        'recent_activity': {
            'new_plans_last_30_days': recent_plans,
            'payments_last_30_days': recent_payments,
        }
    })

@api_view(['GET'])
@permission_classes([IsMerchant])
def payment_trends(request):
    """
    Get payment trends for the last 6 months
    """
    merchant = request.user
    trends = []
    
    for i in range(6):
        start_date = date.today().replace(day=1) - timedelta(days=30*i)
        end_date = (start_date + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        
        month_payments = Installment.objects.filter(
            payment_plan__merchant=merchant,
            paid_date__range=[start_date, end_date],
            status='paid'
        ).aggregate(
            total=Sum('amount'),
            count=Count('id')
        )
        
        trends.append({
            'month': start_date.strftime('%Y-%m'),
            'total_amount': float(month_payments['total'] or 0),
            'payment_count': month_payments['count'] or 0,
        })
    
    return Response({'trends': list(reversed(trends))})