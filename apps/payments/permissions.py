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
    """
    
    def has_object_permission(self, request, view, obj):
        # Only the user (not merchant) can pay installments
        return (
            request.user.email == obj.payment_plan.user_email and
            obj.status == 'pending'
        )