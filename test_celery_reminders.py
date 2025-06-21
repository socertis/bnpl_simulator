#!/usr/bin/env python
"""
Test script for Celery payment reminder functionality
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bnpl_backend.settings')
django.setup()

from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import date, timedelta
from decimal import Decimal
from apps.payments.models import PaymentPlan, Installment
from apps.payments.tasks import (
    send_payment_reminder,
    send_bulk_payment_reminders,
    send_overdue_payment_reminders,
    daily_payment_reminders,
    generate_merchant_payment_report
)

User = get_user_model()

def setup_reminder_test_data():
    """Create test data with various due dates for reminder testing"""
    print("🔧 Setting up reminder test data...")
    
    # Create test merchant
    merchant, created = User.objects.get_or_create(
        email='reminder_merchant@example.com',
        defaults={
            'username': 'reminder_merchant',
            'user_type': 'merchant'
        }
    )
    if created:
        merchant.set_password('password123')
        merchant.save()
    
    # Create payment plan
    payment_plan, created = PaymentPlan.objects.get_or_create(
        merchant=merchant,
        user_email='reminder_customer@example.com',
        total_amount=Decimal('2000.00'),
        number_of_installments=5,
        start_date=date.today() - timedelta(days=30),
        defaults={
            'status': 'active',
            'interest_rate': Decimal('5.0')
        }
    )
    
    if created:
        print(f"✅ Created payment plan {payment_plan.id}")
        
        # Create installments with different due dates for testing
        installments_data = [
            {
                'installment_number': 1,
                'amount': Decimal('400.00'),
                'due_date': date.today() - timedelta(days=10),  # Overdue
                'status': 'pending'
            },
            {
                'installment_number': 2,
                'amount': Decimal('400.00'),
                'due_date': date.today(),  # Due today
                'status': 'pending'
            },
            {
                'installment_number': 3,
                'amount': Decimal('400.00'),
                'due_date': date.today() + timedelta(days=1),  # Due tomorrow
                'status': 'pending'
            },
            {
                'installment_number': 4,
                'amount': Decimal('400.00'),
                'due_date': date.today() + timedelta(days=3),  # Due in 3 days
                'status': 'pending'
            },
            {
                'installment_number': 5,
                'amount': Decimal('400.00'),
                'due_date': date.today() + timedelta(days=30),  # Due in 30 days
                'status': 'pending'
            }
        ]
        
        for data in installments_data:
            Installment.objects.create(
                payment_plan=payment_plan,
                principal_component=Decimal('380.00'),
                interest_component=Decimal('20.00'),
                **data
            )
        
        print(f"✅ Created 5 installments with various due dates")
    else:
        print(f"✅ Using existing payment plan {payment_plan.id}")
    
    return payment_plan, merchant

def test_single_payment_reminder():
    """Test sending a single payment reminder"""
    print("\n🧪 Testing single payment reminder...")
    
    payment_plan, merchant = setup_reminder_test_data()
    
    # Get an installment due in 3 days
    future_installment = Installment.objects.filter(
        payment_plan=payment_plan,
        due_date=date.today() + timedelta(days=3)
    ).first()
    
    if not future_installment:
        print("❌ FAIL: No future installment found for testing")
        return False
    
    print(f"Sending reminder for installment {future_installment.id} due in 3 days")
    
    # Enable eager execution for testing
    settings.CELERY_TASK_ALWAYS_EAGER = True
    
    try:
        result = send_payment_reminder(future_installment.id, 3)
        
        if isinstance(result, dict) and result.get('status') == 'sent':
            print("✅ PASS: Single payment reminder sent successfully")
            print(f"  Recipient: {result['recipient']}")
            print(f"  Type: {result['reminder_type']}")
            return True
        else:
            print(f"❌ FAIL: Unexpected result: {result}")
            return False
            
    except Exception as e:
        print(f"❌ FAIL: Single reminder failed: {e}")
        return False

def test_bulk_payment_reminders():
    """Test sending bulk payment reminders"""
    print("\n🧪 Testing bulk payment reminders...")
    
    payment_plan, merchant = setup_reminder_test_data()
    
    print("Sending bulk reminders for installments due in 3 days")
    
    settings.CELERY_TASK_ALWAYS_EAGER = True
    
    try:
        result = send_bulk_payment_reminders(3)
        
        if isinstance(result, dict) and 'reminders_sent' in result:
            count = result['reminders_sent']
            print(f"✅ PASS: Bulk reminders sent - {count} reminders")
            print(f"  Target date: {result['target_date']}")
            return True
        else:
            print(f"❌ FAIL: Unexpected bulk result: {result}")
            return False
            
    except Exception as e:
        print(f"❌ FAIL: Bulk reminders failed: {e}")
        return False

def test_overdue_payment_reminders():
    """Test sending overdue payment reminders"""
    print("\n🧪 Testing overdue payment reminders...")
    
    payment_plan, merchant = setup_reminder_test_data()
    
    print("Sending overdue payment reminders")
    
    settings.CELERY_TASK_ALWAYS_EAGER = True
    
    try:
        result = send_overdue_payment_reminders()
        
        if isinstance(result, dict):
            marked_late = result.get('marked_late', 0)
            reminders_sent = result.get('overdue_reminders_sent', 0)
            print(f"✅ PASS: Overdue reminders processed")
            print(f"  Marked as late: {marked_late}")
            print(f"  Reminders sent: {reminders_sent}")
            return True
        else:
            print(f"❌ FAIL: Unexpected overdue result: {result}")
            return False
            
    except Exception as e:
        print(f"❌ FAIL: Overdue reminders failed: {e}")
        return False

def test_daily_payment_reminders():
    """Test the daily payment reminders batch"""
    print("\n🧪 Testing daily payment reminders batch...")
    
    payment_plan, merchant = setup_reminder_test_data()
    
    print("Running daily payment reminders batch")
    
    settings.CELERY_TASK_ALWAYS_EAGER = True
    
    try:
        result = daily_payment_reminders()
        
        if isinstance(result, dict) and 'total_reminders_sent' in result:
            total = result['total_reminders_sent']
            print(f"✅ PASS: Daily batch completed - {total} total reminders")
            
            # Show breakdown
            details = result.get('details', {})
            for reminder_type, data in details.items():
                count = data.get('reminders_sent', 0) or data.get('overdue_reminders_sent', 0)
                print(f"  {reminder_type}: {count} reminders")
            
            return True
        else:
            print(f"❌ FAIL: Unexpected daily batch result: {result}")
            return False
            
    except Exception as e:
        print(f"❌ FAIL: Daily batch failed: {e}")
        return False

def test_merchant_report_generation():
    """Test merchant payment report generation"""
    print("\n🧪 Testing merchant report generation...")
    
    payment_plan, merchant = setup_reminder_test_data()
    
    print(f"Generating report for merchant {merchant.id}")
    
    settings.CELERY_TASK_ALWAYS_EAGER = True
    
    try:
        result = generate_merchant_payment_report(merchant.id)
        
        if isinstance(result, dict) and 'merchant_id' in result:
            print("✅ PASS: Merchant report generated successfully")
            print(f"  Merchant: {result['merchant_email']}")
            print(f"  Payment plans: {result['payment_plans']['total']}")
            print(f"  Collection rate: {result['financials']['collection_rate']:.2f}%")
            return True
        else:
            print(f"❌ FAIL: Unexpected report result: {result}")
            return False
            
    except Exception as e:
        print(f"❌ FAIL: Report generation failed: {e}")
        return False

def test_reminder_message_content():
    """Test the content of reminder messages"""
    print("\n🧪 Testing reminder message content...")
    
    payment_plan, merchant = setup_reminder_test_data()
    
    # Get an installment for testing
    test_installment = payment_plan.installments.first()
    
    if not test_installment:
        print("❌ FAIL: No installment found for message testing")
        return False
    
    # Import the message creation function
    from apps.payments.tasks import create_payment_reminder_message
    
    try:
        # Test upcoming reminder
        upcoming_message = create_payment_reminder_message(test_installment, 3, "upcoming")
        if "due in 3 days" in upcoming_message and str(test_installment.amount) in upcoming_message:
            print("✅ PASS: Upcoming reminder message format correct")
        else:
            print("❌ FAIL: Upcoming reminder message format incorrect")
            return False
        
        # Test due today reminder
        due_today_message = create_payment_reminder_message(test_installment, 0, "due_today")
        if "due TODAY" in due_today_message:
            print("✅ PASS: Due today reminder message format correct")
        else:
            print("❌ FAIL: Due today reminder message format incorrect")
            return False
        
        # Test overdue reminder
        overdue_message = create_payment_reminder_message(test_installment, -5, "overdue")
        if "5 days overdue" in overdue_message:
            print("✅ PASS: Overdue reminder message format correct")
        else:
            print("❌ FAIL: Overdue reminder message format incorrect")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ FAIL: Message content testing failed: {e}")
        return False

def test_management_commands():
    """Test management commands"""
    print("\n🧪 Testing management commands...")
    
    from django.core.management import call_command
    from io import StringIO
    
    setup_reminder_test_data()
    
    try:
        # Test payment reminders command
        out = StringIO()
        call_command('send_payment_reminders', '--days-ahead', '3', '--dry-run', stdout=out)
        output = out.getvalue()
        
        if "DRY RUN" in output:
            print("✅ PASS: Payment reminders command working")
        else:
            print("❌ FAIL: Payment reminders command output unexpected")
            return False
        
        # Test merchant reports command
        out = StringIO()
        call_command('generate_merchant_reports', '--all-merchants', '--dry-run', stdout=out)
        output = out.getvalue()
        
        if "DRY RUN" in output or "merchants" in output:
            print("✅ PASS: Merchant reports command working")
        else:
            print("❌ FAIL: Merchant reports command output unexpected")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ FAIL: Management commands failed: {e}")
        return False

def cleanup_reminder_test_data():
    """Clean up test data"""
    print("\n🧹 Cleaning up reminder test data...")
    try:
        PaymentPlan.objects.filter(user_email='reminder_customer@example.com').delete()
        User.objects.filter(email='reminder_merchant@example.com').delete()
        print("✅ Test data cleaned up")
    except Exception as e:
        print(f"⚠️ Cleanup warning: {e}")

if __name__ == '__main__':
    print("🧪 Testing Celery Payment Reminder System\n")
    
    # Store original setting
    original_eager = getattr(settings, 'CELERY_TASK_ALWAYS_EAGER', False)
    
    test_results = []
    
    try:
        test_results.append(("Single Payment Reminder", test_single_payment_reminder()))
        test_results.append(("Bulk Payment Reminders", test_bulk_payment_reminders()))
        test_results.append(("Overdue Payment Reminders", test_overdue_payment_reminders()))
        test_results.append(("Daily Payment Reminders", test_daily_payment_reminders()))
        test_results.append(("Merchant Report Generation", test_merchant_report_generation()))
        test_results.append(("Reminder Message Content", test_reminder_message_content()))
        test_results.append(("Management Commands", test_management_commands()))
        
        print("\n🏁 Test Results Summary:")
        print("=" * 50)
        
        passed = 0
        for test_name, result in test_results:
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{test_name}: {status}")
            if result:
                passed += 1
        
        print(f"\nTotal: {passed}/{len(test_results)} tests passed")
        
        if passed == len(test_results):
            print("🎉 All Celery reminder tests passed!")
        else:
            print("⚠️ Some tests failed - check implementation")
        
        print("\n📋 Celery Setup Instructions:")
        print("To run Celery workers and beat scheduler:")
        print("1. Start Redis: redis-server")
        print("2. Start Celery worker: celery -A bnpl_backend worker --loglevel=info")
        print("3. Start Celery beat: celery -A bnpl_backend beat --loglevel=info")
        print("4. Monitor tasks: celery -A bnpl_backend flower")
            
    except Exception as e:
        print(f"\n❌ Test suite failed with error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Restore original setting
        settings.CELERY_TASK_ALWAYS_EAGER = original_eager
        cleanup_reminder_test_data()