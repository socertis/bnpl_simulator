"""
Test Fixtures for Payment App

This module provides pre-defined test data fixtures that can be easily
imported and used across different test files. These fixtures use the
TestDataSeeder to create consistent, reusable test data.
"""

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken
from decimal import Decimal
from datetime import date, timedelta
from typing import Dict, Any

from .test_data_seeder import TestDataSeeder

User = get_user_model()


class PaymentTestFixtures:
    """
    Collection of test fixtures for payment-related testing
    
    This class provides ready-to-use test data configurations
    that can be easily accessed in test methods.
    """
    
    def __init__(self):
        self.seeder = TestDataSeeder()
        self._fixtures_cache = {}
    
    def get_jwt_token(self, user: User) -> str:
        """
        Get JWT token for a user
        
        Args:
            user: User to generate token for
            
        Returns:
            str: JWT access token
        """
        refresh = RefreshToken.for_user(user)
        return str(refresh.access_token)
    
    def get_auth_headers(self, user: User) -> Dict[str, str]:
        """
        Get authentication headers for API requests
        
        Args:
            user: User to authenticate
            
        Returns:
            Dict: Headers dictionary with Authorization header
        """
        token = self.get_jwt_token(user)
        return {'HTTP_AUTHORIZATION': f'Bearer {token}'}
    
    @property
    def simple_merchant_customer(self) -> Dict[str, Any]:
        """
        Simple merchant-customer fixture with one payment plan
        
        Returns:
            Dict containing:
            - merchant: Merchant user
            - customer: Customer user  
            - payment_plan: Active payment plan
            - installments: List of pending installments
        """
        if 'simple_merchant_customer' not in self._fixtures_cache:
            data = self.seeder.create_test_scenario('basic_merchant_customer')
            self._fixtures_cache['simple_merchant_customer'] = data
        return self._fixtures_cache['simple_merchant_customer']
    
    @property
    def multi_merchant_setup(self) -> Dict[str, Any]:
        """
        Multi-merchant setup for isolation testing
        
        Returns:
            Dict containing:
            - merchants: List of merchant users
            - customers: List of customer users
            - payment_plans: List of payment plans
            - Individual merchant/customer/plan references
        """
        if 'multi_merchant_setup' not in self._fixtures_cache:
            data = self.seeder.create_test_scenario('multiple_merchants')
            self._fixtures_cache['multi_merchant_setup'] = data
        return self._fixtures_cache['multi_merchant_setup']
    
    @property
    def payment_workflow_data(self) -> Dict[str, Any]:
        """
        Payment workflow testing data with installments in different states
        
        Returns:
            Dict containing:
            - merchant: Merchant user
            - customer: Customer user
            - payment_plan: Payment plan
            - pending_installment: Pending installment
            - late_installment: Late installment  
            - paid_installment: Paid installment
        """
        if 'payment_workflow_data' not in self._fixtures_cache:
            data = self.seeder.create_test_scenario('payment_workflow')
            self._fixtures_cache['payment_workflow_data'] = data
        return self._fixtures_cache['payment_workflow_data']
    
    @property
    def edge_cases_data(self) -> Dict[str, Any]:
        """
        Edge cases and error scenarios
        
        Returns:
            Dict containing:
            - invalid_user: User with invalid user_type
            - no_email_customer: Customer without email
            - cancelled_plan: Cancelled payment plan
            - cancelled_installment: Cancelled installment
        """
        if 'edge_cases_data' not in self._fixtures_cache:
            data = self.seeder.create_test_scenario('edge_cases')
            self._fixtures_cache['edge_cases_data'] = data
        return self._fixtures_cache['edge_cases_data']
    
    @property
    def isolation_test_data(self) -> Dict[str, Any]:
        """
        Cross-user isolation testing data
        
        Returns:
            Dict containing:
            - merchants: List of merchant users
            - customers: List of customer users
            - payment_plans: List of payment plans
        """
        if 'isolation_test_data' not in self._fixtures_cache:
            data = self.seeder.create_test_scenario('cross_user_isolation')
            self._fixtures_cache['isolation_test_data'] = data
        return self._fixtures_cache['isolation_test_data']
    
    def create_custom_merchant(self, **kwargs) -> User:
        """Create a custom merchant with specified attributes"""
        return self.seeder.create_merchant(**kwargs)
    
    def create_custom_customer(self, **kwargs) -> User:
        """Create a custom customer with specified attributes"""
        return self.seeder.create_customer(**kwargs)
    
    def create_custom_payment_plan(self, merchant: User, **kwargs) -> Any:
        """Create a custom payment plan with specified attributes"""
        return self.seeder.create_payment_plan(merchant=merchant, **kwargs)
    
    def create_test_installments(self, payment_plan: Any, count: int = 3, **kwargs) -> list:
        """
        Create multiple test installments for a payment plan
        
        Args:
            payment_plan: Payment plan to create installments for
            count: Number of installments to create
            **kwargs: Additional installment attributes
            
        Returns:
            List of created installments
        """
        installments = []
        for i in range(count):
            installment_kwargs = kwargs.copy()
            installment_kwargs.setdefault('installment_number', i + 1)
            installment_kwargs.setdefault('due_date', date.today() + timedelta(days=30 * (i + 1)))
            
            installment = self.seeder.create_installment(payment_plan, **installment_kwargs)
            installments.append(installment)
        
        return installments
    
    def cleanup(self):
        """Clean up all fixture data"""
        self.seeder.cleanup_all()
        self._fixtures_cache.clear()


# Pre-configured test data sets for common scenarios
class CommonTestScenarios:
    """
    Pre-configured test scenarios for common testing needs
    """
    
    @staticmethod
    def security_test_data() -> Dict[str, Any]:
        """
        Data specifically for security testing
        
        Returns:
            Dict with merchants, customers, and plans for security tests
        """
        seeder = TestDataSeeder()
        
        # Create primary test users
        merchant = seeder.create_merchant(
            username='primary_merchant',
            email='primary_merchant@test.com'
        )
        customer = seeder.create_customer(
            username='primary_customer', 
            email='primary_customer@test.com'
        )
        
        # Create other users for isolation testing
        other_merchant = seeder.create_merchant(
            username='other_merchant',
            email='other_merchant@test.com'
        )
        other_customer = seeder.create_customer(
            username='other_customer',
            email='other_customer@test.com'
        )
        
        # Create payment plans
        primary_plan = seeder.create_payment_plan(
            merchant=merchant,
            customer_email=customer.email,
            total_amount=Decimal('1000.00'),
            number_of_installments=3
        )
        
        other_plan = seeder.create_payment_plan(
            merchant=other_merchant,
            customer_email=other_customer.email,
            total_amount=Decimal('500.00'),
            number_of_installments=2
        )
        
        # Create installments
        primary_installments = []
        for i in range(3):
            installment = seeder.create_installment(
                primary_plan,
                installment_number=i + 1,
                status='pending'
            )
            primary_installments.append(installment)
        
        other_installments = []
        for i in range(2):
            installment = seeder.create_installment(
                other_plan,
                installment_number=i + 1,
                status='pending'
            )
            other_installments.append(installment)
        
        return {
            'seeder': seeder,
            'primary_merchant': merchant,
            'primary_customer': customer,
            'other_merchant': other_merchant,
            'other_customer': other_customer,
            'primary_plan': primary_plan,
            'other_plan': other_plan,
            'primary_installments': primary_installments,
            'other_installments': other_installments
        }
    
    @staticmethod
    def functional_test_data() -> Dict[str, Any]:
        """
        Data for functional testing (workflows, business logic)
        
        Returns:
            Dict with comprehensive data for functional tests
        """
        seeder = TestDataSeeder()
        
        merchant = seeder.create_merchant()
        customer = seeder.create_customer()
        
        # Active payment plan with mixed installment statuses
        active_plan = seeder.create_payment_plan(
            merchant=merchant,
            customer_email=customer.email,
            number_of_installments=4,
            status='active'
        )
        
        # Create installments in various states
        pending_installment = seeder.create_installment(
            active_plan,
            installment_number=1,
            status='pending'
        )
        
        late_installment = seeder.create_installment(
            active_plan,
            installment_number=2,
            status='late',
            due_date=date.today() - timedelta(days=5)
        )
        
        paid_installment = seeder.create_installment(
            active_plan,
            installment_number=3,
            status='paid',
            paid_date=timezone.now()
        )
        
        future_installment = seeder.create_installment(
            active_plan,
            installment_number=4,
            status='pending',
            due_date=date.today() + timedelta(days=60)
        )
        
        # Completed payment plan
        completed_plan = seeder.create_payment_plan(
            merchant=merchant,
            customer_email=customer.email,
            number_of_installments=2,
            status='completed'
        )
        
        # All installments paid
        for i in range(2):
            seeder.create_installment(
                completed_plan,
                installment_number=i + 1,
                status='paid',
                paid_date=timezone.now()
            )
        
        return {
            'seeder': seeder,
            'merchant': merchant,
            'customer': customer,
            'active_plan': active_plan,
            'completed_plan': completed_plan,
            'pending_installment': pending_installment,
            'late_installment': late_installment,
            'paid_installment': paid_installment,
            'future_installment': future_installment
        }
    
    @staticmethod
    def validation_test_data() -> Dict[str, Any]:
        """
        Data for validation and error handling tests
        
        Returns:
            Dict with edge cases and validation scenarios
        """
        seeder = TestDataSeeder()
        
        # Valid merchant and customer
        merchant = seeder.create_merchant()
        customer = seeder.create_customer()
        
        # Invalid user scenarios
        invalid_user = User.objects.create_user(
            username='invalid_user',
            email='invalid@test.com',
            password='testpass123',
            user_type='invalid'
        )
        seeder.created_users.append(invalid_user)
        
        no_email_customer = User.objects.create_user(
            username='no_email_customer',
            email='',
            password='testpass123',
            user_type='customer'
        )
        seeder.created_users.append(no_email_customer)
        
        # Cancelled payment plan
        cancelled_plan = seeder.create_payment_plan(
            merchant=merchant,
            customer_email=customer.email,
            status='cancelled'
        )
        
        # Installments in various invalid states
        cancelled_installment = seeder.create_installment(
            cancelled_plan,
            status='cancelled'
        )
        
        return {
            'seeder': seeder,
            'valid_merchant': merchant,
            'valid_customer': customer,
            'invalid_user': invalid_user,
            'no_email_customer': no_email_customer,
            'cancelled_plan': cancelled_plan,
            'cancelled_installment': cancelled_installment
        }
    
    @staticmethod
    def signals_test_data() -> Dict[str, Any]:
        """
        Data specifically for Django signals testing
        
        Returns:
            Dict with merchant, payment plan, and installments for signals tests
        """
        seeder = TestDataSeeder()
        
        merchant = seeder.create_merchant(
            username='signals_merchant',
            email='signals_merchant@test.com'
        )
        
        payment_plan = seeder.create_payment_plan(
            merchant=merchant,
            customer_email='signals_customer@test.com',
            total_amount=Decimal('600.00'),
            number_of_installments=3,
            start_date=date.today()
        )
        
        # Create installments in pending state
        installments = []
        for i in range(3):
            installment = seeder.create_installment(
                payment_plan,
                installment_number=i + 1,
                status='pending',
                due_date=date.today() + timedelta(days=(i + 1) * 30)
            )
            installments.append(installment)
        
        return {
            'seeder': seeder,
            'merchant': merchant,
            'payment_plan': payment_plan,
            'installments': installments
        }