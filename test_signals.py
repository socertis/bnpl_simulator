#!/usr/bin/env python
"""
Test script for Django signals in payment plan status updates
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bnpl_backend.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.utils import timezone
from apps.payments.models import PaymentPlan, Installment
from apps.payments.signals import trigger_payment_plan_status_update, bulk_update_payment_plan_statuses
from decimal import Decimal

User = get_user_model()

def setup_test_data():
    """Create test data for signal testing"""
    print("🔧 Setting up test data...")
    
    # Create test merchant
    merchant, created = User.objects.get_or_create(
        email='test_merchant@example.com',
        defaults={
            'username': 'test_merchant',
            'user_type': 'merchant'
        }
    )
    if created:
        merchant.set_password('password123')
        merchant.save()
    
    # Create test payment plan
    payment_plan, created = PaymentPlan.objects.get_or_create(
        merchant=merchant,
        user_email='test_customer@example.com',
        total_amount=Decimal('1000.00'),
        number_of_installments=3,
        start_date=timezone.now().date(),
        defaults={
            'status': 'active',
            'interest_rate': Decimal('5.0')
        }
    )
    
    if created:
        print(f"✅ Created payment plan {payment_plan.id}")
        
        # Create installments manually (bypassing serializer for testing)
        for i in range(3):
            Installment.objects.create(
                payment_plan=payment_plan,
                installment_number=i + 1,
                amount=Decimal('333.33'),
                principal_component=Decimal('320.00'),
                interest_component=Decimal('13.33'),
                due_date=timezone.now().date()
            )
        print(f"✅ Created 3 installments for payment plan {payment_plan.id}")
    else:
        print(f"✅ Using existing payment plan {payment_plan.id}")
    
    return payment_plan

def test_payment_completion_signal():
    """Test that payment plan status updates when all installments are paid"""
    print("\n🧪 Testing payment completion signal...")
    
    payment_plan = setup_test_data()
    installments = payment_plan.installments.all()
    
    print(f"Initial payment plan status: {payment_plan.status}")
    
    # Pay all installments one by one
    for i, installment in enumerate(installments, 1):
        print(f"Paying installment {i}...")
        installment.status = 'paid'
        installment.paid_date = timezone.now()
        installment.save()
        
        # Refresh payment plan to see signal effect
        payment_plan.refresh_from_db()
        print(f"  Payment plan status after installment {i}: {payment_plan.status}")
    
    # Final check
    if payment_plan.status == 'completed':
        print("✅ PASS: Payment plan marked as completed when all installments paid")
    else:
        print("❌ FAIL: Payment plan not marked as completed")

def test_payment_reactivation_signal():
    """Test that payment plan reactivates when installment status changes"""
    print("\n🧪 Testing payment reactivation signal...")
    
    payment_plan = setup_test_data()
    
    # First complete the payment plan
    for installment in payment_plan.installments.all():
        installment.status = 'paid'
        installment.paid_date = timezone.now()
        installment.save()
    
    payment_plan.refresh_from_db()
    print(f"Payment plan status after completion: {payment_plan.status}")
    
    # Now change one installment back to pending
    first_installment = payment_plan.installments.first()
    first_installment.status = 'pending'
    first_installment.paid_date = None
    first_installment.save()
    
    payment_plan.refresh_from_db()
    print(f"Payment plan status after reactivation: {payment_plan.status}")
    
    if payment_plan.status == 'active':
        print("✅ PASS: Payment plan reactivated when installment changed to pending")
    else:
        print("❌ FAIL: Payment plan not reactivated")

def test_cancellation_signal():
    """Test that payment plan is cancelled when all installments are cancelled"""
    print("\n🧪 Testing cancellation signal...")
    
    payment_plan = setup_test_data()
    
    print(f"Initial payment plan status: {payment_plan.status}")
    
    # Cancel all installments
    for installment in payment_plan.installments.all():
        installment.status = 'cancelled'
        installment.save()
    
    payment_plan.refresh_from_db()
    print(f"Payment plan status after cancelling all installments: {payment_plan.status}")
    
    if payment_plan.status == 'cancelled':
        print("✅ PASS: Payment plan cancelled when all installments cancelled")
    else:
        print("❌ FAIL: Payment plan not cancelled")

def test_utility_functions():
    """Test utility functions for manual status updates"""
    print("\n🧪 Testing utility functions...")
    
    payment_plan = setup_test_data()
    
    # Test manual trigger
    print("Testing manual status update trigger...")
    trigger_payment_plan_status_update(payment_plan)
    print("✅ PASS: Manual trigger completed without errors")
    
    # Test bulk update
    print("Testing bulk status update...")
    updated_count = bulk_update_payment_plan_statuses()
    print(f"✅ PASS: Bulk update completed, {updated_count} plans updated")

def cleanup_test_data():
    """Clean up test data"""
    print("\n🧹 Cleaning up test data...")
    try:
        PaymentPlan.objects.filter(user_email='test_customer@example.com').delete()
        User.objects.filter(email='test_merchant@example.com').delete()
        print("✅ Test data cleaned up")
    except Exception as e:
        print(f"⚠️ Cleanup warning: {e}")

if __name__ == '__main__':
    print("🧪 Testing Django Signals for Payment Plan Status Updates\n")
    
    try:
        test_payment_completion_signal()
        test_payment_reactivation_signal() 
        test_cancellation_signal()
        test_utility_functions()
        
        print("\n🏁 All signal tests completed!")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        cleanup_test_data()