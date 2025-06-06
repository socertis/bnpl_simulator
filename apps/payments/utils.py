from datetime import date
from .models import Installment

def mark_overdue_installments():
    """
    Utility function to mark overdue installments as 'late'
    This can be run as a periodic task
    """
    overdue_installments = Installment.objects.filter(
        status='pending',
        due_date__lt=date.today()
    )
    
    overdue_installments.update(status='late')
    return overdue_installments.count()

def get_payment_plan_summary(payment_plan):
    """
    Get a summary of payment plan status
    """
    installments = payment_plan.installments.all()
    
    return {
        'total_installments': installments.count(),
        'paid_installments': installments.filter(status='paid').count(),
        'pending_installments': installments.filter(status='pending').count(),
        'late_installments': installments.filter(status='late').count(),
        'next_due_date': installments.filter(status='pending').first().due_date if installments.filter(status='pending').exists() else None,
    }