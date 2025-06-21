"""
Test Data Seeder for Payment App Tests

This module provides comprehensive test data seeding and cleanup functionality
for payment-related tests. It creates consistent, isolated test data that can
be used across different test suites.
"""

from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal
from datetime import date, timedelta
from typing import Dict, List, Optional
import logging

from .models import PaymentPlan, Installment

User = get_user_model()
logger = logging.getLogger(__name__)


class TestDataSeeder:
    """
    Comprehensive test data seeder for payment app tests.
    
    Provides methods to create consistent test data including:
    - Users (merchants and customers)
    - Payment plans with various statuses
    - Installments with different payment states
    - Edge case scenarios for testing
    """
    
    def __init__(self):
        """Initialize the seeder"""
        self.created_users = []
        self.created_payment_plans = []
        self.created_installments = []
        self._seed_counter = 0
    
    def get_unique_identifier(self) -> str:
        """Get a unique identifier for test data"""
        self._seed_counter += 1
        return f"test_{self._seed_counter}_{timezone.now().strftime('%H%M%S')}"
    
    def create_merchant(self, **kwargs) -> User:
        """
        Create a merchant user for testing
        
        Args:
            **kwargs: Additional user fields to override defaults
            
        Returns:
            User: Created merchant user
        """
        unique_id = self.get_unique_identifier()
        defaults = {
            'username': f'merchant_{unique_id}',
            'email': f'merchant_{unique_id}@test.com',
            'password': 'testpass123',
            'user_type': 'merchant',
            'first_name': 'Test',
            'last_name': 'Merchant'
        }
        defaults.update(kwargs)
        
        user = User.objects.create_user(**defaults)
        self.created_users.append(user)
        logger.debug(f"Created merchant user: {user.username}")
        return user
    
    def create_customer(self, **kwargs) -> User:
        """
        Create a customer user for testing
        
        Args:
            **kwargs: Additional user fields to override defaults
            
        Returns:
            User: Created customer user
        """
        unique_id = self.get_unique_identifier()
        defaults = {
            'username': f'customer_{unique_id}',
            'email': f'customer_{unique_id}@test.com',
            'password': 'testpass123',
            'user_type': 'customer',
            'first_name': 'Test',
            'last_name': 'Customer'
        }
        defaults.update(kwargs)
        
        user = User.objects.create_user(**defaults)
        self.created_users.append(user)
        logger.debug(f"Created customer user: {user.username}")
        return user
    
    def create_payment_plan(self, merchant: User, customer_email: str = None, **kwargs) -> PaymentPlan:
        """
        Create a payment plan for testing
        
        Args:
            merchant: Merchant user who owns the plan
            customer_email: Email of the customer (optional, will generate if not provided)
            **kwargs: Additional payment plan fields to override defaults
            
        Returns:
            PaymentPlan: Created payment plan
        """
        if not customer_email:
            customer_email = f'customer_{self.get_unique_identifier()}@test.com'
        
        defaults = {
            'merchant': merchant,
            'user_email': customer_email,
            'total_amount': Decimal('1000.00'),
            'number_of_installments': 3,
            'start_date': date.today() + timedelta(days=1),
            'interest_rate': Decimal('5.0'),
            'tenor_type': 'month',
            'status': 'active'
        }
        defaults.update(kwargs)
        
        payment_plan = PaymentPlan.objects.create(**defaults)
        self.created_payment_plans.append(payment_plan)
        logger.debug(f"Created payment plan: {payment_plan.id}")
        return payment_plan
    
    def create_installment(self, payment_plan: PaymentPlan, **kwargs) -> Installment:
        """
        Create an installment for testing
        
        Args:
            payment_plan: Payment plan this installment belongs to
            **kwargs: Additional installment fields to override defaults
            
        Returns:
            Installment: Created installment
        """
        installment_count = payment_plan.installments.count() + 1
        
        defaults = {
            'payment_plan': payment_plan,
            'installment_number': installment_count,
            'amount': Decimal('333.33'),
            'principal_component': Decimal('320.00'),
            'interest_component': Decimal('13.33'),
            'due_date': date.today() + timedelta(days=30 * installment_count),
            'status': 'pending'
        }
        defaults.update(kwargs)
        
        installment = Installment.objects.create(**defaults)
        self.created_installments.append(installment)
        logger.debug(f"Created installment: {installment.id}")
        return installment
    
    def create_test_scenario(self, scenario_name: str) -> Dict:
        """
        Create predefined test scenarios with multiple related objects
        
        Args:
            scenario_name: Name of the scenario to create
            
        Returns:
            Dict: Dictionary containing created objects for the scenario
        """
        scenarios = {
            'basic_merchant_customer': self._create_basic_merchant_customer_scenario,
            'multiple_merchants': self._create_multiple_merchants_scenario,
            'payment_workflow': self._create_payment_workflow_scenario,
            'edge_cases': self._create_edge_cases_scenario,
            'cross_user_isolation': self._create_cross_user_isolation_scenario
        }
        
        if scenario_name not in scenarios:
            raise ValueError(f"Unknown scenario: {scenario_name}. Available: {list(scenarios.keys())}")
        
        return scenarios[scenario_name]()
    
    def _create_basic_merchant_customer_scenario(self) -> Dict:
        """Create basic merchant-customer scenario"""
        merchant = self.create_merchant()
        customer = self.create_customer()
        
        payment_plan = self.create_payment_plan(
            merchant=merchant,
            customer_email=customer.email
        )
        
        installments = []
        for i in range(payment_plan.number_of_installments):
            installments.append(self.create_installment(payment_plan))
        
        return {
            'merchant': merchant,
            'customer': customer,
            'payment_plan': payment_plan,
            'installments': installments
        }
    
    def _create_multiple_merchants_scenario(self) -> Dict:
        """Create scenario with multiple merchants and customers"""
        merchant1 = self.create_merchant(username='merchant_1', email='merchant1@test.com')
        merchant2 = self.create_merchant(username='merchant_2', email='merchant2@test.com')
        
        customer1 = self.create_customer(username='customer_1', email='customer1@test.com')
        customer2 = self.create_customer(username='customer_2', email='customer2@test.com')
        
        # Merchant 1's plan for customer 1
        plan1 = self.create_payment_plan(
            merchant=merchant1,
            customer_email=customer1.email,
            total_amount=Decimal('1500.00')
        )
        
        # Merchant 2's plan for customer 2
        plan2 = self.create_payment_plan(
            merchant=merchant2,
            customer_email=customer2.email,
            total_amount=Decimal('800.00'),
            number_of_installments=2
        )
        
        return {
            'merchants': [merchant1, merchant2],
            'customers': [customer1, customer2],
            'payment_plans': [plan1, plan2],
            'merchant1': merchant1,
            'merchant2': merchant2,
            'customer1': customer1,
            'customer2': customer2,
            'plan1': plan1,
            'plan2': plan2
        }
    
    def _create_payment_workflow_scenario(self) -> Dict:
        """Create scenario for testing payment workflows"""
        merchant = self.create_merchant()
        customer = self.create_customer()
        
        payment_plan = self.create_payment_plan(
            merchant=merchant,
            customer_email=customer.email,
            number_of_installments=3
        )
        
        # Create installments with different statuses
        pending_installment = self.create_installment(
            payment_plan,
            installment_number=1,
            status='pending'
        )
        
        late_installment = self.create_installment(
            payment_plan,
            installment_number=2,
            status='late',
            due_date=date.today() - timedelta(days=5)
        )
        
        paid_installment = self.create_installment(
            payment_plan,
            installment_number=3,
            status='paid',
            paid_date=timezone.now()
        )
        
        return {
            'merchant': merchant,
            'customer': customer,
            'payment_plan': payment_plan,
            'pending_installment': pending_installment,
            'late_installment': late_installment,
            'paid_installment': paid_installment,
            'all_installments': [pending_installment, late_installment, paid_installment]
        }
    
    def _create_edge_cases_scenario(self) -> Dict:
        """Create scenario for testing edge cases"""
        # User with invalid user_type
        invalid_user = User.objects.create_user(
            username='invalid_user',
            email='invalid@test.com',
            password='testpass123',
            user_type='invalid'
        )
        self.created_users.append(invalid_user)
        
        # Customer without email
        no_email_customer = User.objects.create_user(
            username='no_email_customer',
            email='',
            password='testpass123',
            user_type='customer'
        )
        self.created_users.append(no_email_customer)
        
        # Merchant for cancelled plan
        merchant = self.create_merchant()
        
        # Cancelled payment plan
        cancelled_plan = self.create_payment_plan(
            merchant=merchant,
            status='cancelled',
            customer_email='cancelled_customer@test.com'
        )
        
        # Cancelled installment
        cancelled_installment = self.create_installment(
            cancelled_plan,
            status='cancelled'
        )
        
        return {
            'invalid_user': invalid_user,
            'no_email_customer': no_email_customer,
            'merchant': merchant,
            'cancelled_plan': cancelled_plan,
            'cancelled_installment': cancelled_installment
        }
    
    def _create_cross_user_isolation_scenario(self) -> Dict:
        """Create scenario for testing cross-user isolation"""
        # Create multiple merchants and customers
        merchants = [self.create_merchant() for _ in range(3)]
        customers = [self.create_customer() for _ in range(3)]
        
        plans = []
        for i, (merchant, customer) in enumerate(zip(merchants, customers)):
            plan = self.create_payment_plan(
                merchant=merchant,
                customer_email=customer.email,
                total_amount=Decimal(f'{(i+1)*500}.00')
            )
            plans.append(plan)
            
            # Create some installments
            for j in range(2):
                self.create_installment(plan)
        
        return {
            'merchants': merchants,
            'customers': customers,
            'payment_plans': plans
        }
    
    def cleanup_all(self):
        """
        Clean up all created test data
        
        This method removes all test data created by this seeder instance.
        It's designed to be called in test tearDown methods.
        """
        try:
            # Delete in reverse order of creation to handle foreign key constraints
            
            # Delete installments first
            if self.created_installments:
                installment_ids = [inst.id for inst in self.created_installments if inst.id]
                deleted_installments = Installment.objects.filter(id__in=installment_ids).delete()
                logger.debug(f"Deleted {deleted_installments[0]} installments")
            
            # Delete payment plans
            if self.created_payment_plans:
                plan_ids = [plan.id for plan in self.created_payment_plans if plan.id]
                deleted_plans = PaymentPlan.objects.filter(id__in=plan_ids).delete()
                logger.debug(f"Deleted {deleted_plans[0]} payment plans")
            
            # Delete users
            if self.created_users:
                user_ids = [user.id for user in self.created_users if user.id]
                deleted_users = User.objects.filter(id__in=user_ids).delete()
                logger.debug(f"Deleted {deleted_users[0]} users")
            
            # Clear tracking lists
            self.created_installments.clear()
            self.created_payment_plans.clear()
            self.created_users.clear()
            self._seed_counter = 0
            
            logger.info("Test data cleanup completed successfully")
            
        except Exception as e:
            logger.error(f"Error during test data cleanup: {e}")
            raise
    
    def get_summary(self) -> Dict:
        """
        Get summary of created test data
        
        Returns:
            Dict: Summary of created objects
        """
        return {
            'users_created': len(self.created_users),
            'payment_plans_created': len(self.created_payment_plans),
            'installments_created': len(self.created_installments),
            'merchants': [u for u in self.created_users if u.user_type == 'merchant'],
            'customers': [u for u in self.created_users if u.user_type == 'customer'],
            'active_plans': [p for p in self.created_payment_plans if p.status == 'active'],
            'cancelled_plans': [p for p in self.created_payment_plans if p.status == 'cancelled']
        }


class BaseTestWithSeeder:
    """
    Base test class that provides seeding functionality
    
    Inherit from this class to get automatic test data seeding and cleanup.
    """
    
    def setUp(self):
        """Set up test with seeder"""
        super().setUp() if hasattr(super(), 'setUp') else None
        self.seeder = TestDataSeeder()
        self.seed_test_data()
    
    def tearDown(self):
        """Clean up test data"""
        if hasattr(self, 'seeder'):
            self.seeder.cleanup_all()
        super().tearDown() if hasattr(super(), 'tearDown') else None
    
    def seed_test_data(self):
        """
        Override this method in test classes to create specific test data
        
        Example:
            def seed_test_data(self):
                self.test_data = self.seeder.create_test_scenario('basic_merchant_customer')
                self.merchant = self.test_data['merchant']
                self.customer = self.test_data['customer']
        """
        pass