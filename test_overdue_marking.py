#!/usr/bin/env python
"""
Test script for automatic overdue installment marking functionality
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bnpl_backend.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import date, timedelta
from decimal import Decimal
from apps.payments.models import PaymentPlan, Installment
from apps.payments.signals import (
    mark_all_overdue_installments, 
    check_installment_overdue_status,
    get_overdue_installments_report
)
from apps.payments.utils import mark_overdue_installments

User = get_user_model()

def setup_overdue_test_data():
    """Create test data with overdue installments"""
    print("🔧 Setting up overdue test data...")
    
    # Create test merchant
    merchant, created = User.objects.get_or_create(
        email='overdue_merchant@example.com',
        defaults={
            'username': 'overdue_merchant',
            'user_type': 'merchant'
        }
    )
    if created:
        merchant.set_password('password123')
        merchant.save()
    
    # Create payment plan
    payment_plan, created = PaymentPlan.objects.get_or_create(
        merchant=merchant,
        user_email='overdue_customer@example.com',
        total_amount=Decimal('1200.00'),
        number_of_installments=4,
        start_date=date.today() - timedelta(days=60),  # Started 60 days ago
        defaults={
            'status': 'active',
            'interest_rate': Decimal('5.0')
        }
    )
    
    if created:
        print(f"✅ Created payment plan {payment_plan.id}")
        
        # Create installments with different overdue scenarios
        installments_data = [
            {
                'installment_number': 1,
                'amount': Decimal('300.00'),
                'due_date': date.today() - timedelta(days=30),  # 30 days overdue
                'status': 'pending'
            },
            {
                'installment_number': 2,
                'amount': Decimal('300.00'),
                'due_date': date.today() - timedelta(days=15),  # 15 days overdue
                'status': 'pending'
            },
            {
                'installment_number': 3,
                'amount': Decimal('300.00'),
                'due_date': date.today() - timedelta(days=5),   # 5 days overdue
                'status': 'pending'
            },
            {
                'installment_number': 4,
                'amount': Decimal('300.00'),
                'due_date': date.today() + timedelta(days=15),  # Future due date
                'status': 'pending'
            }
        ]
        
        for data in installments_data:
            Installment.objects.create(
                payment_plan=payment_plan,
                principal_component=Decimal('285.00'),
                interest_component=Decimal('15.00'),
                **data
            )
        
        print(f"✅ Created 4 installments with mixed due dates")
    else:
        print(f"✅ Using existing payment plan {payment_plan.id}")
    
    return payment_plan

def test_overdue_report_generation():
    """Test overdue installments report generation"""
    print("\n🧪 Testing overdue report generation...")
    
    payment_plan = setup_overdue_test_data()
    
    # Generate report
    report = get_overdue_installments_report()
    
    print(f"Report data: {report}")
    
    if 'error' in report:
        print(f"❌ FAIL: Report generation failed: {report['error']}")
        return False
    
    # Validate report structure
    expected_keys = ['overdue_pending_count', 'late_count', 'total_overdue', 'report_date']
    for key in expected_keys:
        if key not in report:
            print(f"❌ FAIL: Missing key '{key}' in report")
            return False
    
    print(f"✅ PASS: Report generated successfully")
    print(f"  - Overdue pending: {report['overdue_pending_count']}")
    print(f"  - Already late: {report['late_count']}")
    print(f"  - Total overdue: {report['total_overdue']}")
    
    return True

def test_automatic_overdue_marking():
    """Test automatic marking of overdue installments"""
    print("\n🧪 Testing automatic overdue marking...")
    
    payment_plan = setup_overdue_test_data()
    
    # Reset all installments to pending
    Installment.objects.filter(payment_plan=payment_plan).update(status='pending')
    
    # Count overdue installments before
    overdue_before = Installment.objects.filter(
        payment_plan=payment_plan,
        status='pending',
        due_date__lt=date.today()
    ).count()
    
    print(f"Overdue installments before marking: {overdue_before}")
    
    # Mark overdue installments
    updated_count = mark_all_overdue_installments()
    
    # Count late installments after
    late_after = Installment.objects.filter(
        payment_plan=payment_plan,
        status='late'
    ).count()
    
    print(f"Late installments after marking: {late_after}")
    print(f"Updated count reported: {updated_count}")
    
    if late_after == overdue_before and updated_count == overdue_before:
        print("✅ PASS: All overdue installments marked as late")
        return True
    else:
        print("❌ FAIL: Mismatch in overdue marking")
        return False

def test_single_installment_check():
    """Test individual installment overdue checking"""
    print("\n🧪 Testing single installment overdue check...")
    
    payment_plan = setup_overdue_test_data()
    
    # Get an overdue installment
    overdue_installment = Installment.objects.filter(
        payment_plan=payment_plan,
        due_date__lt=date.today()
    ).first()
    
    if not overdue_installment:
        print("❌ FAIL: No overdue installment found for testing")
        return False
    
    # Reset to pending
    overdue_installment.status = 'pending'
    overdue_installment.save()
    
    print(f"Testing installment {overdue_installment.id} - due: {overdue_installment.due_date}")
    
    # Check overdue status
    was_updated = check_installment_overdue_status(overdue_installment)
    
    # Refresh from database
    overdue_installment.refresh_from_db()
    
    if was_updated and overdue_installment.status == 'late':
        print("✅ PASS: Individual installment marked as late")
        return True
    else:
        print(f"❌ FAIL: Individual check failed - status: {overdue_installment.status}, updated: {was_updated}")
        return False

def test_utils_integration():
    """Test utils.py integration with overdue marking"""
    print("\n🧪 Testing utils.py integration...")
    
    payment_plan = setup_overdue_test_data()
    
    # Reset all to pending
    Installment.objects.filter(payment_plan=payment_plan).update(status='pending')
    
    # Use utils function
    try:
        updated_count = mark_overdue_installments()
        print(f"Utils function updated {updated_count} installments")
        
        # Verify results
        late_count = Installment.objects.filter(
            payment_plan=payment_plan,
            status='late'
        ).count()
        
        if late_count > 0:
            print("✅ PASS: Utils integration working")
            return True
        else:
            print("❌ FAIL: Utils function didn't mark any installments")
            return False
            
    except Exception as e:
        print(f"❌ FAIL: Utils integration failed: {e}")
        return False

def test_signal_based_real_time_checking():
    """Test real-time overdue checking via signals"""
    print("\n🧪 Testing real-time signal-based checking...")
    
    payment_plan = setup_overdue_test_data()
    
    # Create a new overdue installment
    overdue_installment = Installment.objects.create(
        payment_plan=payment_plan,
        installment_number=5,
        amount=Decimal('100.00'),
        principal_component=Decimal('95.00'),
        interest_component=Decimal('5.00'),
        due_date=date.today() - timedelta(days=1),  # 1 day overdue
        status='pending'
    )
    
    print(f"Created installment {overdue_installment.id} that is 1 day overdue")
    
    # The signal should have already fired, but let's check by saving again
    overdue_installment.save()
    
    # Refresh to see if signal updated it
    overdue_installment.refresh_from_db()
    
    if overdue_installment.status == 'late':
        print("✅ PASS: Signal-based real-time checking working")
        return True
    else:
        print(f"❌ FAIL: Signal didn't mark installment as late - status: {overdue_installment.status}")
        return False

def test_management_command_dry_run():
    """Test the management command in dry-run mode"""
    print("\n🧪 Testing management command (dry-run simulation)...")
    
    from django.core.management import call_command
    from io import StringIO
    
    setup_overdue_test_data()
    
    try:
        # Capture command output
        out = StringIO()
        call_command('mark_overdue_installments', '--dry-run', '--verbose', stdout=out)
        output = out.getvalue()
        
        print("Command output preview:")
        print(output[:200] + "..." if len(output) > 200 else output)
        
        if "DRY RUN" in output:
            print("✅ PASS: Management command dry-run working")
            return True
        else:
            print("❌ FAIL: Management command output unexpected")
            return False
            
    except Exception as e:
        print(f"❌ FAIL: Management command failed: {e}")
        return False

def cleanup_overdue_test_data():
    """Clean up test data"""
    print("\n🧹 Cleaning up overdue test data...")
    try:
        PaymentPlan.objects.filter(user_email='overdue_customer@example.com').delete()
        User.objects.filter(email='overdue_merchant@example.com').delete()
        print("✅ Test data cleaned up")
    except Exception as e:
        print(f"⚠️ Cleanup warning: {e}")

if __name__ == '__main__':
    print("🧪 Testing Automatic Overdue Installment Marking\n")
    
    test_results = []
    
    try:
        test_results.append(("Report Generation", test_overdue_report_generation()))
        test_results.append(("Automatic Marking", test_automatic_overdue_marking()))
        test_results.append(("Single Installment Check", test_single_installment_check()))
        test_results.append(("Utils Integration", test_utils_integration()))
        test_results.append(("Real-time Signals", test_signal_based_real_time_checking()))
        test_results.append(("Management Command", test_management_command_dry_run()))
        
        print("\n🏁 Test Results Summary:")
        print("=" * 40)
        
        passed = 0
        for test_name, result in test_results:
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{test_name}: {status}")
            if result:
                passed += 1
        
        print(f"\nTotal: {passed}/{len(test_results)} tests passed")
        
        if passed == len(test_results):
            print("🎉 All overdue marking tests passed!")
        else:
            print("⚠️ Some tests failed - check implementation")
            
    except Exception as e:
        print(f"\n❌ Test suite failed with error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        cleanup_overdue_test_data()