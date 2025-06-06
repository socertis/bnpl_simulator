from rest_framework import status, viewsets, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone
from .models import PaymentPlan, Installment
from .serializers import (
    PaymentPlanCreateSerializer, 
    PaymentPlanSerializer, 
    InstallmentSerializer
)
from .permissions import IsOwnerOrMerchant, CanPayInstallment
from apps.authentication.permissions import IsMerchant

class PaymentPlanViewSet(viewsets.ModelViewSet):
    serializer_class = PaymentPlanSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return PaymentPlanCreateSerializer
        return PaymentPlanSerializer
    
    def get_queryset(self):
        user = self.request.user
        if user.user_type == 'merchant':
            # Merchants see plans they created
            return PaymentPlan.objects.filter(merchant=user)
        else:
            # Users see plans assigned to them
            return PaymentPlan.objects.filter(user_email=user.email)
    
    def get_permissions(self):
        if self.action == 'create':
            return [IsMerchant()]
        return [permissions.IsAuthenticated(), IsOwnerOrMerchant()]

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def pay_installment(request, installment_id):
    """
    Simulate payment of an installment
    """
    installment = get_object_or_404(Installment, id=installment_id)
    
    # Check permissions
    permission = CanPayInstallment()
    if not permission.has_object_permission(request, None, installment):
        return Response(
            {'error': 'You do not have permission to pay this installment'}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Process payment
    installment.status = 'paid'
    installment.paid_date = timezone.now()
    installment.save()
    
    # Check if all installments are paid
    payment_plan = installment.payment_plan
    if payment_plan.installments.filter(status='paid').count() == payment_plan.number_of_installments:
        payment_plan.status = 'completed'
        payment_plan.save()
    
    return Response({
        'message': 'Payment successful',
        'installment': InstallmentSerializer(installment).data
    })

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def dashboard_stats(request):
    """
    Get dashboard statistics for the current user
    """
    user = request.user
    
    if user.user_type == 'merchant':
        plans = PaymentPlan.objects.filter(merchant=user)
        total_revenue = sum(plan.total_amount for plan in plans)
        active_plans = plans.filter(status='active').count()
        completed_plans = plans.filter(status='completed').count()
        
        return Response({
            'total_plans': plans.count(),
            'active_plans': active_plans,
            'completed_plans': completed_plans,
            'total_revenue': total_revenue,
        })
    else:
        plans = PaymentPlan.objects.filter(user_email=user.email)
        total_amount = sum(plan.total_amount for plan in plans)
        pending_installments = Installment.objects.filter(
            payment_plan__user_email=user.email,
            status='pending'
        ).count()
        
        return Response({
            'total_plans': plans.count(),
            'total_amount': total_amount,
            'pending_installments': pending_installments,
        })