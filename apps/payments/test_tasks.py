from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.core import mail
from unittest.mock import patch, Mock
from datetime import date, timedelta
from decimal import Decimal
from celery import current_app
from .models import PaymentPlan, Installment
from .tasks import (
    check_overdue_installments,
    send_payment_reminder,
    send_payment_reminders,
    send_payment_confirmation,
    generate_merchant_report
)

User = get_user_model()

# Use eager task execution for testing
@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
class CeleryTaskTest(TestCase):
    """Test Celery tasks"""
    
    def setUp(self):
        # Configure Celery for testing
        current_app.conf.task_always_eager = True
        current_app.conf.task_eager_propagates = True
        
        self.merchant = User.objects.create_user(
            username='merchant',
            email='merchant@test.com',
            password='testpass123',
            user_type='merchant'
        )
        
        self.plan = PaymentPlan.objects.create(
            merchant=self.merchant,
            user_email='customer@test.com',
            total_amount=Decimal('1000.00'),
            number_of_installments=4,
            start_date=date.today()
        )
    
    def test_check_overdue_installments_task(self):
        """Test overdue installments check task"""
        # Create overdue installment
        overdue_installment = Installment.objects.create(
            payment_plan=self.plan,
            installment_number=1,
            amount=Decimal('250.00'),
            due_date=date.today() - timedelta(days=1),
            status='pending'
        )
        
        # Create future installment
        future_installment = Installment.objects.create(
            payment_plan=self.plan,
            installment_number=2,
            amount=Decimal('250.00'),
            due_date=date.today() + timedelta(days=1),
            status='pending'
        )
        
        # Run task
        result = check_overdue_installments.delay()
        result_message = result.get()
        
        # Check results
        overdue_installment.refresh_from_db()
        future_installment.refresh_from_db()
        
        self.assertEqual(overdue_installment.status, 'late')
        self.assertEqual(future_installment.status, 'pending')
        self.assertIn('1', result_message)  # Should process 1 overdue installment
    
    def test_send_payment_reminder_task(self):
        """Test payment reminder task"""
        installment = Installment.objects.create(
            payment_plan=self.plan,
            installment_number=1,
            amount=Decimal('250.00'),
            due_date=date.today() + timedelta(days=3)
        )
        
        # Clear mail outbox
        mail.outbox = []
        
        # Run task
        result = send_payment_reminder.delay(installment.id)
        result_message = result.get()
        
        # Check email was sent
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Payment Reminder', mail.outbox[0].subject)
        self.assertIn('customer@test.com', mail.outbox[0].to)
        self.assertIn('250', mail.outbox[0].body)
        self.assertIn('successfully', result_message)
    
    def test_send_payment_reminder_nonexistent_installment(self):
        """Test payment reminder for non-existent installment"""
        result = send_payment_reminder.delay(99999)
        result_message = result.get()
        
        self.assertIn('not found', result_message)
        self.assertEqual(len(mail.outbox), 0)
    
    def test_send_payment_reminders_task(self):
        """Test batch payment reminders task"""
        # Create installment due in 3 days
        reminder_date = date.today() + timedelta(days=3)
        installment1 = Installment.objects.create(
            payment_plan=self.plan,
            installment_number=1,
            amount=Decimal('250.00'),
            due_date=reminder_date
        )
        
        # Create another plan and installment
        plan2 = PaymentPlan.objects.create(
            merchant=self.merchant,
            user_email='customer2@test.com',
            total_amount=Decimal('500.00'),
            number_of_installments=2,
            start_date=date.today()
        )
        
        installment2 = Installment.objects.create(
            payment_plan=plan2,
            installment_number=1,
            amount=Decimal('250.00'),
            due_date=reminder_date
        )
        
        # Create installment not due for reminders
        installment3 = Installment.objects.create(
            payment_plan=self.plan,
            installment_number=2,
            amount=Decimal('250.00'),
            due_date=date.today() + timedelta(days=10)
        )
        
        # Clear mail outbox
        mail.outbox = []
        
        # Mock the individual reminder task to avoid double execution
        with patch('apps.payments.tasks.send_payment_reminder.delay') as mock_task:
            result = send_payment_reminders.delay()
            result_message = result.get()
            
            # Should queue 2 reminder tasks
            self.assertEqual(mock_task.call_count, 2)
            self.assertIn('2', result_message)
    
    def test_send_payment_confirmation_task(self):
        """Test payment confirmation task"""
        installment = Installment.objects.create(
            payment_plan=self.plan,
            installment_number=1,
            amount=Decimal('250.00'),
            due_date=date.today(),
            status='paid',
            paid_date=date.today()
        )
        
        # Clear mail outbox
        mail.outbox = []
        
        # Run task
        result = send_payment_confirmation.delay(installment.id)
        result_message = result.get()
        
        # Check email was sent
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Payment Confirmation', mail.outbox[0].subject)
        self.assertIn('customer@test.com', mail.outbox[0].to)
        self.assertIn('250', mail.outbox[0].body)
        self.assertIn('successfully processed', mail.outbox[0].body)
    
    def test_generate_merchant_report_task(self):
        """Test merchant report generation task"""
        # Create some test data
        plan1 = PaymentPlan.objects.create(
            merchant=self.merchant,
            user_email='user1@test.com',
            total_amount=Decimal('1000.00'),
            number_of_installments=4,
            start_date=date.today(),
            status='completed'
        )
        
        plan2 = PaymentPlan.objects.create(
            merchant=self.merchant,
            user_email='user2@test.com',
            total_amount=Decimal('500.00'),
            number_of_installments=2,
            start_date=date.today(),
            status='active'
        )
        
        # Clear mail outbox
        mail.outbox = []
        
        # Run task
        result = generate_merchant_report.delay(self.merchant.id, 'monthly')
        result_message = result.get()
        
        # Check email was sent
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Monthly Report', mail.outbox[0].subject)
        self.assertIn('merchant@test.com', mail.outbox[0].to)
        self.assertIn('1500', mail.outbox[0].body)  # Total revenue
        self.assertIn('Report sent', result_message)