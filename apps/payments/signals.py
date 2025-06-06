from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Installment, PaymentPlan

@receiver(post_save, sender=Installment)
def update_payment_plan_status(sender, instance, **kwargs):
    """
    Update payment plan status when an installment is paid
    """
    payment_plan = instance.payment_plan
    
    # Check if all installments are paid
    paid_count = payment_plan.installments.filter(status='paid').count()
    total_count = payment_plan.number_of_installments
    
    if paid_count == total_count and payment_plan.status != 'completed':
        payment_plan.status = 'completed'
        payment_plan.save()