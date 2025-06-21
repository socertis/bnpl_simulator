from rest_framework import permissions

class IsOwnerOrMerchant(permissions.BasePermission):
    """
    Custom permission to only allow owners of a payment plan or merchants to access it.
    """
    
    def has_object_permission(self, request, view, obj):
        # For PaymentPlan objects
        if hasattr(obj, 'user_email'):
            return (
                request.user.email == obj.user_email or 
                obj.merchant == request.user
            )
        
        # For Installment objects
        if hasattr(obj, 'payment_plan'):
            return (
                request.user.email == obj.payment_plan.user_email or 
                obj.payment_plan.merchant == request.user
            )
        
        return False

class CanPayInstallment(permissions.BasePermission):
    """
    Permission to check if user can pay an installment
    - Only users (not merchants) can pay installments
    - User must be the owner of the payment plan
    - Installment must be in 'pending' or 'late' status
    """
    
    def has_permission(self, request, view):
        # Basic authentication and user check
        user = request.user
        if not user or not user.is_authenticated:
            return False
        
        if user.user_type != 'user':
            return False
            
        return True
    
    def has_object_permission(self, request, view, obj):
        user = request.user
        
        # User must be the owner of the payment plan
        if user.email != obj.payment_plan.user_email:
            return False
        
        # Installment must be payable (pending or late)
        if obj.status not in ['pending', 'late']:
            return False
            
        # Payment plan must be active
        if obj.payment_plan.status != 'active':
            return False
            
        return True