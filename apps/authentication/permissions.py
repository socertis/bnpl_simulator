from rest_framework import permissions

class IsMerchant(permissions.BasePermission):
    """
    Custom permission to only allow merchants to access certain views.
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.user_type == 'merchant'

class IsUser(permissions.BasePermission):
    """
    Custom permission to only allow regular users to access certain views.
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.user_type == 'user'

class IsOwnerOrMerchant(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object or merchants to access it.
    """
    def has_object_permission(self, request, view, obj):
        # Check if user is the owner or a merchant
        if hasattr(obj, 'user_email'):
            return (request.user.email == obj.user_email or 
                   request.user.user_type == 'merchant')
        return False