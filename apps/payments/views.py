from rest_framework import status, viewsets, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db import transaction
import logging
from .models import PaymentPlan, Installment
from .serializers import (
    PaymentPlanCreateSerializer, 
    PaymentPlanSerializer, 
    InstallmentSerializer
)
from .permissions import IsOwnerOrMerchant, CanPayInstallment
from apps.authentication.permissions import IsMerchant

logger = logging.getLogger(__name__)

class PaymentPlanViewSet(viewsets.ModelViewSet):
    serializer_class = PaymentPlanSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return PaymentPlanCreateSerializer
        return PaymentPlanSerializer
    
    def get_queryset(self):
        user = self.request.user
        
        # Ensure user is authenticated and has a valid user_type
        if not user.is_authenticated or not hasattr(user, 'user_type'):
            return PaymentPlan.objects.none()
        
        if user.user_type == 'merchant':
            # Merchants see only plans they created
            return PaymentPlan.objects.filter(merchant=user).select_related('merchant')
        elif user.user_type == 'user':
            # Users see only plans assigned to their email
            if not user.email:
                return PaymentPlan.objects.none()
            return PaymentPlan.objects.filter(user_email=user.email).select_related('merchant')
        else:
            # Invalid user_type - return empty queryset
            return PaymentPlan.objects.none()
    
    def get_permissions(self):
        if self.action == 'create':
            return [permissions.IsAuthenticated(), IsMerchant()]
        return [permissions.IsAuthenticated(), IsOwnerOrMerchant()]

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def pay_installment(request, installment_id):
    """
    Simulate payment of an installment with comprehensive error handling
    """
    try:
        # Ensure only users can pay installments
        if request.user.user_type != 'user':
            return Response(
                {'error': 'Only customers can make payments'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Validate installment ID
        if not installment_id or not str(installment_id).isdigit():
            return Response(
                {'error': 'Invalid installment ID'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        installment = get_object_or_404(Installment, id=installment_id)
        
        # Check permissions
        permission = CanPayInstallment()
        if not permission.has_object_permission(request, None, installment):
            return Response(
                {'error': 'You do not have permission to pay this installment'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Validate installment can be paid
        if installment.status == 'paid':
            return Response(
                {'error': 'Installment has already been paid'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if installment.status == 'cancelled':
            return Response(
                {'error': 'Cannot pay a cancelled installment'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate payment plan is active
        payment_plan = installment.payment_plan
        if payment_plan.status not in ['active']:
            return Response(
                {'error': f'Cannot pay installment for {payment_plan.status} payment plan'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Process payment atomically
        with transaction.atomic():
            # Lock the installment for update
            installment = Installment.objects.select_for_update().get(id=installment_id)
            
            # Double-check status after lock
            if installment.status == 'paid':
                return Response(
                    {'error': 'Installment has already been paid'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Update installment (status update will be handled by signals)
            installment.status = 'paid'
            installment.paid_date = timezone.now()
            installment.save()
            
            # Get the updated payment plan status (signals will have updated it)
            payment_plan = installment.payment_plan
            payment_plan.refresh_from_db()
            
            logger.info(f"Installment {installment.id} paid successfully")
        
        return Response({
            'message': 'Payment successful',
            'installment': InstallmentSerializer(installment).data,
            'payment_plan_status': payment_plan.status
        })
        
    except ValidationError as e:
        logger.error(f"Validation error in pay_installment: {e}")
        return Response(
            {'error': str(e)}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        logger.error(f"Unexpected error in pay_installment: {e}")
        return Response(
            {'error': 'An unexpected error occurred while processing payment'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def dashboard_stats(request):
    """
    Get dashboard statistics for the current user with error handling
    """
    try:
        user = request.user
        
        if not user or not hasattr(user, 'user_type'):
            return Response(
                {'error': 'Invalid user'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if user.user_type == 'merchant':
            try:
                plans = PaymentPlan.objects.filter(merchant=user)
                
                # Calculate stats with error handling
                total_revenue = sum(plan.total_amount for plan in plans) if plans.exists() else 0
                active_plans = plans.filter(status='active').count()
                completed_plans = plans.filter(status='completed').count()
                cancelled_plans = plans.filter(status='cancelled').count()
                
                return Response({
                    'user_type': 'merchant',
                    'total_plans': plans.count(),
                    'active_plans': active_plans,
                    'completed_plans': completed_plans,
                    'cancelled_plans': cancelled_plans,
                    'total_revenue': float(total_revenue),
                })
                
            except Exception as e:
                logger.error(f"Error calculating merchant stats: {e}")
                return Response(
                    {'error': 'Failed to calculate merchant statistics'}, 
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        else:  # Regular user
            try:
                if not user.email:
                    return Response(
                        {'error': 'User email is required'}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                plans = PaymentPlan.objects.filter(user_email=user.email)
                
                # Calculate stats with error handling
                total_amount = sum(plan.total_amount for plan in plans) if plans.exists() else 0
                
                pending_installments = Installment.objects.filter(
                    payment_plan__user_email=user.email,
                    status='pending'
                ).count()
                
                late_installments = Installment.objects.filter(
                    payment_plan__user_email=user.email,
                    status='late'
                ).count()
                
                paid_installments = Installment.objects.filter(
                    payment_plan__user_email=user.email,
                    status='paid'
                ).count()
                
                return Response({
                    'user_type': 'customer',
                    'total_plans': plans.count(),
                    'total_amount': float(total_amount),
                    'pending_installments': pending_installments,
                    'late_installments': late_installments,
                    'paid_installments': paid_installments,
                })
                
            except Exception as e:
                logger.error(f"Error calculating customer stats: {e}")
                return Response(
                    {'error': 'Failed to calculate customer statistics'}, 
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
    
    except Exception as e:
        logger.error(f"Unexpected error in dashboard_stats: {e}")
        return Response(
            {'error': 'An unexpected error occurred'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated, IsMerchant])
def get_interest_rate(request):
    """
    Get the current interest rate for merchants
    """
    try:
        from decouple import config
        
        interest_rate = config('DEFAULT_INTEREST_RATE', default=0.47, cast=float)
        
        return Response({
            'interest_rate': float(interest_rate),
            'rate_type': 'annual_percentage_rate'
        })
        
    except Exception as e:
        logger.error(f"Error retrieving interest rate: {e}")
        return Response(
            {'error': 'Failed to retrieve interest rate'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )