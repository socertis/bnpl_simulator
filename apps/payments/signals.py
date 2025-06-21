from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
from datetime import date
import logging
from .models import Installment, PaymentPlan

logger = logging.getLogger(__name__)

@receiver(post_save, sender=Installment)
def update_payment_plan_status_on_save(sender, instance, created, **kwargs):
    """
    Update payment plan status when an installment is saved
    Handles completion, reactivation, and cancellation scenarios
    """
    try:
        payment_plan = instance.payment_plan
        
        # Prevent recursive saves by checking if we're already updating
        if hasattr(payment_plan, '_updating_status'):
            return
            
        payment_plan._updating_status = True
        
        try:
            # Get current installment counts
            installments = payment_plan.installments.all()
            total_count = payment_plan.number_of_installments
            paid_count = installments.filter(status='paid').count()
            cancelled_count = installments.filter(status='cancelled').count()
            pending_count = installments.filter(status='pending').count()
            late_count = installments.filter(status='late').count()
            
            # Determine new status based on installment statuses
            new_status = payment_plan.status
            
            # All installments paid -> completed
            if paid_count == total_count and total_count > 0:
                new_status = 'completed'
                logger.info(f"Payment plan {payment_plan.id} completed - all installments paid")
            
            # All installments cancelled -> cancelled
            elif cancelled_count == total_count and total_count > 0:
                new_status = 'cancelled'
                logger.info(f"Payment plan {payment_plan.id} cancelled - all installments cancelled")
            
            # Payment plan was completed but now has non-paid installments -> reactivate
            elif payment_plan.status == 'completed' and paid_count < total_count:
                new_status = 'active'
                logger.info(f"Payment plan {payment_plan.id} reactivated - installment status changed")
            
            # Payment plan was cancelled but now has active installments -> reactivate
            elif payment_plan.status == 'cancelled' and (pending_count > 0 or late_count > 0 or paid_count > 0):
                new_status = 'active'
                logger.info(f"Payment plan {payment_plan.id} reactivated from cancelled status")
            
            # Update status if changed
            if new_status != payment_plan.status:
                payment_plan.status = new_status
                payment_plan.save(update_fields=['status', 'updated_at'])
                logger.info(f"Payment plan {payment_plan.id} status updated: {payment_plan.status} -> {new_status}")
                
        finally:
            # Clean up the flag
            if hasattr(payment_plan, '_updating_status'):
                delattr(payment_plan, '_updating_status')
                
    except Exception as e:
        logger.error(f"Error updating payment plan status for installment {instance.id}: {e}")

@receiver(post_delete, sender=Installment)
def update_payment_plan_status_on_delete(sender, instance, **kwargs):
    """
    Update payment plan status when an installment is deleted
    """
    try:
        payment_plan = instance.payment_plan
        
        # Prevent recursive operations
        if hasattr(payment_plan, '_updating_status'):
            return
            
        payment_plan._updating_status = True
        
        try:
            # Recalculate status after installment deletion
            remaining_installments = payment_plan.installments.all()
            
            if remaining_installments.count() == 0:
                # No installments left - reset to active if not cancelled
                if payment_plan.status != 'cancelled':
                    payment_plan.status = 'active'
                    payment_plan.save(update_fields=['status', 'updated_at'])
                    logger.info(f"Payment plan {payment_plan.id} reset to active - no installments remaining")
            else:
                # Trigger status recalculation by touching an installment
                first_installment = remaining_installments.first()
                if first_installment:
                    # This will trigger the post_save signal above
                    first_installment.save(update_fields=['updated_at'])
                    
        finally:
            if hasattr(payment_plan, '_updating_status'):
                delattr(payment_plan, '_updating_status')
                
    except Exception as e:
        logger.error(f"Error updating payment plan status after installment deletion: {e}")

@receiver(post_save, sender=PaymentPlan)
def validate_payment_plan_status(sender, instance, created, **kwargs):
    """
    Validate payment plan status consistency when payment plan is saved
    This signal ensures the status is logical given the current installments
    """
    # Skip validation during creation or if we're already updating
    if created or hasattr(instance, '_updating_status'):
        return
        
    try:
        # Check for status inconsistencies
        installments = instance.installments.all()
        
        if installments.exists():
            paid_count = installments.filter(status='paid').count()
            total_count = instance.number_of_installments
            cancelled_count = installments.filter(status='cancelled').count()
            
            # Log potential inconsistencies
            if instance.status == 'completed' and paid_count < total_count:
                logger.warning(f"Payment plan {instance.id} marked completed but only {paid_count}/{total_count} installments paid")
            
            elif instance.status == 'active' and paid_count == total_count and total_count > 0:
                logger.warning(f"Payment plan {instance.id} marked active but all installments are paid")
                
            elif instance.status == 'cancelled' and cancelled_count < total_count:
                logger.warning(f"Payment plan {instance.id} marked cancelled but only {cancelled_count}/{total_count} installments cancelled")
                
    except Exception as e:
        logger.error(f"Error validating payment plan {instance.id} status: {e}")

def trigger_payment_plan_status_update(payment_plan):
    """
    Utility function to manually trigger payment plan status update
    Useful for batch operations or manual corrections
    """
    try:
        if payment_plan.installments.exists():
            # Trigger signal by saving the first installment
            first_installment = payment_plan.installments.first()
            first_installment.save(update_fields=['updated_at'])
        else:
            logger.warning(f"Payment plan {payment_plan.id} has no installments for status update")
    except Exception as e:
        logger.error(f"Error triggering status update for payment plan {payment_plan.id}: {e}")

def bulk_update_payment_plan_statuses():
    """
    Utility function to update all payment plan statuses
    Useful for data migration or fixing inconsistencies
    """
    try:
        payment_plans = PaymentPlan.objects.all()
        updated_count = 0
        
        for payment_plan in payment_plans:
            old_status = payment_plan.status
            trigger_payment_plan_status_update(payment_plan)
            
            # Refresh from database to check if status changed
            payment_plan.refresh_from_db()
            if payment_plan.status != old_status:
                updated_count += 1
                logger.info(f"Updated payment plan {payment_plan.id}: {old_status} -> {payment_plan.status}")
        
        logger.info(f"Bulk status update completed: {updated_count} payment plans updated")
        return updated_count
        
    except Exception as e:
        logger.error(f"Error during bulk payment plan status update: {e}")
        return 0

@receiver(post_save, sender=Installment)
def check_overdue_on_save(sender, instance, created, **kwargs):
    """
    Check if installment is overdue when saved and mark as late
    This provides real-time overdue detection
    """
    try:
        # Only check for pending installments
        if instance.status == 'pending' and instance.is_overdue:
            logger.info(f"Marking overdue installment {instance.id} as late")
            
            # Use update to avoid triggering this signal again
            Installment.objects.filter(id=instance.id).update(
                status='late',
                updated_at=timezone.now()
            )
            
            # Log the change
            logger.info(f"Installment {instance.id} marked as late due to overdue date: {instance.due_date}")
            
    except Exception as e:
        logger.error(f"Error checking overdue status for installment {instance.id}: {e}")

def mark_all_overdue_installments():
    """
    Mark all overdue pending installments as late
    This function can be called manually or by scheduled tasks
    """
    try:
        # Find all overdue pending installments
        overdue_installments = Installment.objects.filter(
            status='pending',
            due_date__lt=date.today()
        )
        
        count = overdue_installments.count()
        if count == 0:
            logger.info("No overdue installments found")
            return 0
        
        # Update all at once for efficiency
        updated_count = overdue_installments.update(
            status='late',
            updated_at=timezone.now()
        )
        
        logger.info(f"Marked {updated_count} overdue installments as late")
        
        # Log details of marked installments
        for installment in overdue_installments:
            logger.info(f"Installment {installment.id} (plan {installment.payment_plan.id}) marked late - due: {installment.due_date}")
        
        return updated_count
        
    except Exception as e:
        logger.error(f"Error marking overdue installments as late: {e}")
        return 0

def check_installment_overdue_status(installment):
    """
    Check and update a single installment's overdue status
    Returns True if status was changed, False otherwise
    """
    try:
        if installment.status == 'pending' and installment.is_overdue:
            old_status = installment.status
            installment.status = 'late'
            installment.save(update_fields=['status', 'updated_at'])
            
            logger.info(f"Installment {installment.id} changed from {old_status} to late")
            return True
            
        return False
        
    except Exception as e:
        logger.error(f"Error checking overdue status for installment {installment.id}: {e}")
        return False

def get_overdue_installments_report():
    """
    Generate a report of all overdue installments
    Returns a dictionary with statistics and details
    """
    try:
        # Get overdue pending installments
        overdue_pending = Installment.objects.filter(
            status='pending',
            due_date__lt=date.today()
        ).select_related('payment_plan', 'payment_plan__merchant')
        
        # Get already marked late installments
        late_installments = Installment.objects.filter(
            status='late'
        ).select_related('payment_plan', 'payment_plan__merchant')
        
        # Calculate statistics
        overdue_count = overdue_pending.count()
        late_count = late_installments.count()
        
        # Group by payment plan
        overdue_plans = {}
        for installment in overdue_pending:
            plan_id = installment.payment_plan.id
            if plan_id not in overdue_plans:
                overdue_plans[plan_id] = {
                    'payment_plan': installment.payment_plan,
                    'overdue_installments': []
                }
            overdue_plans[plan_id]['overdue_installments'].append(installment)
        
        return {
            'overdue_pending_count': overdue_count,
            'late_count': late_count,
            'total_overdue': overdue_count + late_count,
            'overdue_plans': overdue_plans,
            'overdue_installments': list(overdue_pending),
            'late_installments': list(late_installments),
            'report_date': date.today()
        }
        
    except Exception as e:
        logger.error(f"Error generating overdue report: {e}")
        return {
            'error': str(e),
            'report_date': date.today()
        }