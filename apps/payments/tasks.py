from celery import shared_task
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from datetime import date, timedelta
import logging
from .models import Installment, PaymentPlan
from .signals import mark_all_overdue_installments

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3)
def send_payment_reminder(self, installment_id, days_until_due=None):
    """
    Send a payment reminder for a specific installment
    """
    try:
        installment = Installment.objects.select_related('payment_plan').get(id=installment_id)
        
        # Calculate days until due if not provided
        if days_until_due is None:
            days_until_due = (installment.due_date - date.today()).days
        
        # Skip if installment is already paid or cancelled
        if installment.status in ['paid', 'cancelled']:
            logger.info(f"Skipping reminder for installment {installment_id} - status: {installment.status}")
            return f"Skipped - installment {installment_id} is {installment.status}"
        
        # Determine reminder type based on days until due
        if days_until_due > 0:
            reminder_type = "upcoming"
            subject = f"Payment Reminder: Installment Due in {days_until_due} Days"
            urgency = "upcoming"
        elif days_until_due == 0:
            reminder_type = "due_today"
            subject = "Payment Reminder: Installment Due Today"
            urgency = "due"
        else:
            reminder_type = "overdue"
            days_overdue = abs(days_until_due)
            subject = f"Overdue Payment: Installment {days_overdue} Days Late"
            urgency = "overdue"
        
        # Create mock email content
        message = create_payment_reminder_message(installment, days_until_due, reminder_type)
        
        # Mock email sending (log instead of actual email)
        mock_send_email(
            to_email=installment.payment_plan.user_email,
            subject=subject,
            message=message,
            installment=installment,
            reminder_type=reminder_type
        )
        
        # Log the reminder
        logger.info(
            f"Payment reminder sent for installment {installment_id} "
            f"({reminder_type}, {days_until_due} days, {urgency})"
        )
        
        return {
            'installment_id': installment_id,
            'reminder_type': reminder_type,
            'days_until_due': days_until_due,
            'status': 'sent',
            'recipient': installment.payment_plan.user_email
        }
        
    except Installment.DoesNotExist:
        error_msg = f"Installment {installment_id} not found"
        logger.error(error_msg)
        return {'error': error_msg}
    
    except Exception as e:
        error_msg = f"Failed to send reminder for installment {installment_id}: {str(e)}"
        logger.error(error_msg)
        
        # Retry logic
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying reminder for installment {installment_id} (attempt {self.request.retries + 1})")
            raise self.retry(countdown=60 * (self.request.retries + 1))  # Exponential backoff
        
        return {'error': error_msg, 'installment_id': installment_id}

@shared_task
def send_bulk_payment_reminders(days_ahead=3):
    """
    Send payment reminders for all installments due in X days
    """
    try:
        target_date = date.today() + timedelta(days=days_ahead)
        
        # Find installments due on the target date
        upcoming_installments = Installment.objects.filter(
            due_date=target_date,
            status__in=['pending', 'late']
        ).select_related('payment_plan')
        
        reminder_count = upcoming_installments.count()
        
        if reminder_count == 0:
            logger.info(f"No installments due in {days_ahead} days ({target_date})")
            return {
                'days_ahead': days_ahead,
                'target_date': str(target_date),
                'reminders_sent': 0,
                'message': 'No installments found'
            }
        
        logger.info(f"Sending {reminder_count} payment reminders for installments due on {target_date}")
        
        # Send individual reminders asynchronously
        sent_tasks = []
        for installment in upcoming_installments:
            task = send_payment_reminder.delay(installment.id, days_ahead)
            sent_tasks.append(task.id)
        
        return {
            'days_ahead': days_ahead,
            'target_date': str(target_date),
            'reminders_sent': reminder_count,
            'task_ids': sent_tasks,
            'message': f'Sent {reminder_count} payment reminders'
        }
        
    except Exception as e:
        error_msg = f"Failed to send bulk reminders: {str(e)}"
        logger.error(error_msg)
        return {'error': error_msg}

@shared_task
def send_overdue_payment_reminders():
    """
    Send reminders for overdue installments and mark them as late
    """
    try:
        # First, mark overdue installments as late
        marked_late = mark_all_overdue_installments()
        logger.info(f"Marked {marked_late} installments as late")
        
        # Find overdue installments (now marked as late)
        overdue_installments = Installment.objects.filter(
            status='late',
            due_date__lt=date.today()
        ).select_related('payment_plan')
        
        overdue_count = overdue_installments.count()
        
        if overdue_count == 0:
            return {
                'marked_late': marked_late,
                'overdue_reminders_sent': 0,
                'message': 'No overdue installments found'
            }
        
        logger.info(f"Sending {overdue_count} overdue payment reminders")
        
        # Send overdue reminders
        sent_tasks = []
        for installment in overdue_installments:
            days_overdue = (date.today() - installment.due_date).days
            task = send_payment_reminder.delay(installment.id, -days_overdue)
            sent_tasks.append(task.id)
        
        return {
            'marked_late': marked_late,
            'overdue_reminders_sent': overdue_count,
            'task_ids': sent_tasks,
            'message': f'Sent {overdue_count} overdue reminders'
        }
        
    except Exception as e:
        error_msg = f"Failed to send overdue reminders: {str(e)}"
        logger.error(error_msg)
        return {'error': error_msg}

@shared_task
def daily_payment_reminders():
    """
    Daily task to send all payment reminders
    Combines upcoming and overdue reminders
    """
    try:
        results = {}
        
        # Send 3-day advance reminders
        results['3_day_reminders'] = send_bulk_payment_reminders.delay(3).get()
        
        # Send 1-day advance reminders
        results['1_day_reminders'] = send_bulk_payment_reminders.delay(1).get()
        
        # Send due today reminders
        results['due_today_reminders'] = send_bulk_payment_reminders.delay(0).get()
        
        # Send overdue reminders
        results['overdue_reminders'] = send_overdue_payment_reminders.delay().get()
        
        # Calculate totals
        total_sent = sum([
            results['3_day_reminders'].get('reminders_sent', 0),
            results['1_day_reminders'].get('reminders_sent', 0),
            results['due_today_reminders'].get('reminders_sent', 0),
            results['overdue_reminders'].get('overdue_reminders_sent', 0)
        ])
        
        logger.info(f"Daily payment reminders completed: {total_sent} total reminders sent")
        
        return {
            'total_reminders_sent': total_sent,
            'execution_date': str(date.today()),
            'details': results
        }
        
    except Exception as e:
        error_msg = f"Daily payment reminders failed: {str(e)}"
        logger.error(error_msg)
        return {'error': error_msg}

@shared_task
def generate_merchant_payment_report(merchant_id):
    """
    Generate payment status report for a specific merchant
    """
    try:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        merchant = User.objects.get(id=merchant_id, user_type='merchant')
        
        # Get merchant's payment plans
        payment_plans = PaymentPlan.objects.filter(merchant=merchant)
        
        # Calculate statistics
        total_plans = payment_plans.count()
        active_plans = payment_plans.filter(status='active').count()
        completed_plans = payment_plans.filter(status='completed').count()
        
        # Get installment statistics
        total_installments = Installment.objects.filter(payment_plan__merchant=merchant).count()
        paid_installments = Installment.objects.filter(payment_plan__merchant=merchant, status='paid').count()
        pending_installments = Installment.objects.filter(payment_plan__merchant=merchant, status='pending').count()
        late_installments = Installment.objects.filter(payment_plan__merchant=merchant, status='late').count()
        
        # Calculate financial metrics
        total_revenue = sum(plan.total_amount for plan in payment_plans)
        collected_amount = sum(
            installment.amount for installment in 
            Installment.objects.filter(payment_plan__merchant=merchant, status='paid')
        )
        outstanding_amount = total_revenue - collected_amount
        
        report = {
            'merchant_id': merchant_id,
            'merchant_email': merchant.email,
            'report_date': str(date.today()),
            'payment_plans': {
                'total': total_plans,
                'active': active_plans,
                'completed': completed_plans
            },
            'installments': {
                'total': total_installments,
                'paid': paid_installments,
                'pending': pending_installments,
                'late': late_installments
            },
            'financials': {
                'total_revenue': float(total_revenue),
                'collected_amount': float(collected_amount),
                'outstanding_amount': float(outstanding_amount),
                'collection_rate': (float(collected_amount) / float(total_revenue) * 100) if total_revenue > 0 else 0
            }
        }
        
        # Mock report delivery (log instead of email)
        mock_send_report(merchant.email, report)
        
        logger.info(f"Payment report generated for merchant {merchant_id}")
        
        return report
        
    except Exception as e:
        error_msg = f"Failed to generate merchant report for {merchant_id}: {str(e)}"
        logger.error(error_msg)
        return {'error': error_msg, 'merchant_id': merchant_id}

def create_payment_reminder_message(installment, days_until_due, reminder_type):
    """
    Create the payment reminder message content
    """
    payment_plan = installment.payment_plan
    
    if reminder_type == "upcoming":
        message = f"""
Dear Customer,

This is a friendly reminder that your installment payment is due in {days_until_due} days.

Payment Details:
- Installment Number: {installment.installment_number} of {payment_plan.number_of_installments}
- Amount Due: {installment.amount} SAR
- Due Date: {installment.due_date}
- Payment Plan ID: {payment_plan.id}

Please ensure your payment is completed by the due date to avoid any late fees.

Thank you for your business!

BNPL Payment System
        """
    elif reminder_type == "due_today":
        message = f"""
Dear Customer,

Your installment payment is due TODAY.

Payment Details:
- Installment Number: {installment.installment_number} of {payment_plan.number_of_installments}
- Amount Due: {installment.amount} SAR
- Due Date: {installment.due_date} (TODAY)
- Payment Plan ID: {payment_plan.id}

Please complete your payment today to avoid late fees.

BNPL Payment System
        """
    else:  # overdue
        days_overdue = abs(days_until_due)
        message = f"""
Dear Customer,

Your installment payment is now {days_overdue} days overdue.

Payment Details:
- Installment Number: {installment.installment_number} of {payment_plan.number_of_installments}
- Amount Due: {installment.amount} SAR
- Original Due Date: {installment.due_date}
- Days Overdue: {days_overdue}
- Payment Plan ID: {payment_plan.id}

Please complete your payment immediately to avoid further complications.

BNPL Payment System
        """
    
    return message.strip()

def mock_send_email(to_email, subject, message, installment, reminder_type):
    """
    Mock email sending function that logs instead of sending actual emails
    """
    print(f"\n📧 MOCK EMAIL SENT")
    print(f"To: {to_email}")
    print(f"Subject: {subject}")
    print(f"Type: {reminder_type}")
    print(f"Installment: {installment.id}")
    print(f"Amount: {installment.amount} SAR")
    print("-" * 50)
    print(message)
    print("=" * 50)
    
    # Log to Django logger as well
    logger.info(
        f"Mock email sent - To: {to_email}, Subject: {subject}, "
        f"Installment: {installment.id}, Type: {reminder_type}"
    )

def mock_send_report(merchant_email, report):
    """
    Mock report delivery function
    """
    print(f"\n📊 MOCK REPORT DELIVERED")
    print(f"To: {merchant_email}")
    print(f"Report Date: {report['report_date']}")
    print(f"Payment Plans: {report['payment_plans']['total']}")
    print(f"Collection Rate: {report['financials']['collection_rate']:.2f}%")
    print("=" * 50)
    
    logger.info(f"Mock report delivered to {merchant_email}")