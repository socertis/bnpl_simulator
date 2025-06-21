"""
Example Test Cases Using the New Seeding System

This file demonstrates how to use the new test data seeding system
in various testing scenarios. Use these examples as a reference
for writing new tests.
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from decimal import Decimal

from .test_data_seeder import TestDataSeeder, BaseTestWithSeeder
from .test_fixtures import PaymentTestFixtures, CommonTestScenarios
from .models import PaymentPlan, Installment

User = get_user_model()


class ExampleBasicSeederUsageTestCase(APITestCase):
    """
    Example: Basic usage of the seeding system
    
    This example shows the most straightforward way to use the seeder
    for creating test data and cleaning it up.
    """
    
    def setUp(self):
        """Set up test with manual seeder usage"""
        self.seeder = TestDataSeeder()
        
        # Create basic test data
        self.merchant = self.seeder.create_merchant()
        self.customer = self.seeder.create_customer()
        self.payment_plan = self.seeder.create_payment_plan(
            merchant=self.merchant,
            customer_email=self.customer.email
        )
        
        # Create some installments
        self.installments = []
        for i in range(3):
            installment = self.seeder.create_installment(self.payment_plan)
            self.installments.append(installment)
    
    def tearDown(self):
        """Clean up test data"""
        self.seeder.cleanup_all()
    
    def get_jwt_token(self, user):
        """Helper method for JWT token generation"""
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(user)
        return str(refresh.access_token)
    
    def authenticate_user(self, user):
        """Helper method for user authentication"""
        token = self.get_jwt_token(user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
    
    def test_merchant_can_view_own_plans(self):
        """Test that merchant can view their own payment plans"""
        self.authenticate_user(self.merchant)
        
        url = reverse('paymentplan-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], self.payment_plan.id)
    
    def test_customer_can_pay_installment(self):
        """Test that customer can pay their installment"""
        self.authenticate_user(self.customer)
        
        installment = self.installments[0]
        url = reverse('pay_installment', kwargs={'installment_id': installment.id})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], 'Payment successful')
        
        # Verify installment was marked as paid
        installment.refresh_from_db()
        self.assertEqual(installment.status, 'paid')


class ExampleScenarioBasedTestCase(APITestCase):
    """
    Example: Using pre-defined scenarios
    
    This example shows how to use the CommonTestScenarios class
    to get pre-configured test data for specific testing needs.
    """
    
    def setUp(self):
        """Set up using predefined scenarios"""
        # Get comprehensive security test data
        self.security_data = CommonTestScenarios.security_test_data()
        
        # Get functional test data  
        self.functional_data = CommonTestScenarios.functional_test_data()
    
    def tearDown(self):
        """Clean up all scenario data"""
        self.security_data['seeder'].cleanup_all()
        self.functional_data['seeder'].cleanup_all()
    
    def get_jwt_token(self, user):
        """Helper method for JWT token generation"""
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(user)
        return str(refresh.access_token)
    
    def authenticate_user(self, user):
        """Helper method for user authentication"""
        token = self.get_jwt_token(user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
    
    def test_cross_merchant_isolation(self):
        """Test that merchants cannot see other merchants' data"""
        primary_merchant = self.security_data['primary_merchant']
        other_merchant = self.security_data['other_merchant']
        
        # Authenticate as primary merchant
        self.authenticate_user(primary_merchant)
        
        url = reverse('paymentplan-list')
        response = self.client.get(url)
        
        # Should only see own plans
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        plan_ids = [plan['id'] for plan in response.data['results']]
        self.assertIn(self.security_data['primary_plan'].id, plan_ids)
        self.assertNotIn(self.security_data['other_plan'].id, plan_ids)
    
    def test_payment_workflow_with_mixed_statuses(self):
        """Test payment workflow with installments in different states"""
        customer = self.functional_data['customer']
        pending_installment = self.functional_data['pending_installment']
        late_installment = self.functional_data['late_installment']
        paid_installment = self.functional_data['paid_installment']
        
        self.authenticate_user(customer)
        
        # Should be able to pay pending installment
        url = reverse('pay_installment', kwargs={'installment_id': pending_installment.id})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Should be able to pay late installment
        url = reverse('pay_installment', kwargs={'installment_id': late_installment.id})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Should not be able to pay already paid installment
        url = reverse('pay_installment', kwargs={'installment_id': paid_installment.id})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class ExampleFixturesBasedTestCase(APITestCase):
    """
    Example: Using PaymentTestFixtures for dynamic scenarios
    
    This example shows how to use the PaymentTestFixtures class
    for more dynamic test data creation with easy access patterns.
    """
    
    def setUp(self):
        """Set up using fixtures"""
        self.fixtures = PaymentTestFixtures()
    
    def tearDown(self):
        """Clean up fixture data"""
        self.fixtures.cleanup()
    
    def test_simple_merchant_customer_workflow(self):
        """Test basic merchant-customer workflow using fixtures"""
        # Get simple scenario data
        data = self.fixtures.simple_merchant_customer
        merchant = data['merchant']
        customer = data['customer']
        payment_plan = data['payment_plan']
        installments = data['installments']
        
        # Test merchant can view the plan
        self.client.credentials(**self.fixtures.get_auth_headers(merchant))
        
        url = reverse('paymentplan-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        
        # Test customer can pay installment
        self.client.credentials(**self.fixtures.get_auth_headers(customer))
        
        url = reverse('pay_installment', kwargs={'installment_id': installments[0].id})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_multi_merchant_isolation(self):
        """Test multi-merchant isolation using fixtures"""
        # Get multi-merchant scenario
        data = self.fixtures.multi_merchant_setup
        merchant1 = data['merchant1']
        merchant2 = data['merchant2']
        plan1 = data['plan1']
        plan2 = data['plan2']
        
        # Test merchant1 can only see their plan
        self.client.credentials(**self.fixtures.get_auth_headers(merchant1))
        
        url = reverse('paymentplan-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        plan_ids = [plan['id'] for plan in response.data['results']]
        self.assertIn(plan1.id, plan_ids)
        self.assertNotIn(plan2.id, plan_ids)
    
    def test_custom_scenario_creation(self):
        """Test creating custom scenarios with fixtures"""
        # Create custom merchant and customer
        custom_merchant = self.fixtures.create_custom_merchant(
            username='custom_merchant',
            email='custom@merchant.com'
        )
        
        custom_customer = self.fixtures.create_custom_customer(
            username='custom_customer',
            email='custom@customer.com'
        )
        
        # Create custom payment plan
        custom_plan = self.fixtures.create_custom_payment_plan(
            merchant=custom_merchant,
            customer_email=custom_customer.email,
            total_amount=Decimal('2500.00'),
            number_of_installments=5
        )
        
        # Create custom installments
        installments = self.fixtures.create_test_installments(
            payment_plan=custom_plan,
            count=3,
            status='pending'
        )
        
        # Test the custom scenario
        self.assertEqual(len(installments), 3)
        self.assertEqual(custom_plan.total_amount, Decimal('2500.00'))
        
        # Test authentication works
        self.client.credentials(**self.fixtures.get_auth_headers(custom_merchant))
        
        url = reverse('paymentplan-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class ExampleInheritanceBasedTestCase(BaseTestWithSeeder, APITestCase):
    """
    Example: Using inheritance for automatic seeding
    
    This example shows how to inherit from BaseTestWithSeeder
    to get automatic test data setup and cleanup.
    """
    
    def seed_test_data(self):
        """Override to define specific test data for this class"""
        # Create test scenario
        self.test_data = self.seeder.create_test_scenario('basic_merchant_customer')
        
        # Extract commonly used objects
        self.merchant = self.test_data['merchant']
        self.customer = self.test_data['customer']
        self.payment_plan = self.test_data['payment_plan']
        self.installments = self.test_data['installments']
    
    def get_jwt_token(self, user):
        """Helper method for JWT token generation"""
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(user)
        return str(refresh.access_token)
    
    def authenticate_user(self, user):
        """Helper method for user authentication"""
        token = self.get_jwt_token(user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
    
    def test_automatic_seeding_works(self):
        """Test that automatic seeding works correctly"""
        # Test data should be automatically available
        self.assertIsNotNone(self.merchant)
        self.assertIsNotNone(self.customer)
        self.assertIsNotNone(self.payment_plan)
        self.assertEqual(len(self.installments), 3)
        
        # Test basic functionality
        self.authenticate_user(self.customer)
        
        url = reverse('pay_installment', kwargs={'installment_id': self.installments[0].id})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_seeder_provides_unique_data(self):
        """Test that seeder provides unique data across test methods"""
        # Each test method should get fresh data
        self.assertIsNotNone(self.merchant.email)
        self.assertTrue('@test.com' in self.merchant.email)
        
        # Test that we can create additional data if needed
        extra_merchant = self.seeder.create_merchant()
        self.assertNotEqual(self.merchant.email, extra_merchant.email)


class ExampleValidationTestCase(APITestCase):
    """
    Example: Testing validation and edge cases
    
    This example shows how to test validation scenarios
    using the validation test data.
    """
    
    def setUp(self):
        """Set up validation test data"""
        self.validation_data = CommonTestScenarios.validation_test_data()
    
    def tearDown(self):
        """Clean up validation data"""
        self.validation_data['seeder'].cleanup_all()
    
    def get_jwt_token(self, user):
        """Helper method for JWT token generation"""
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(user)
        return str(refresh.access_token)
    
    def authenticate_user(self, user):
        """Helper method for user authentication"""
        token = self.get_jwt_token(user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
    
    def test_invalid_user_type_handling(self):
        """Test handling of invalid user types"""
        invalid_user = self.validation_data['invalid_user']
        
        self.authenticate_user(invalid_user)
        
        url = reverse('paymentplan-list')
        response = self.client.get(url)
        
        # Should return empty results for invalid user type
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 0)
    
    def test_cancelled_payment_plan_handling(self):
        """Test handling of cancelled payment plans"""
        cancelled_plan = self.validation_data['cancelled_plan']
        cancelled_installment = self.validation_data['cancelled_installment']
        valid_customer = self.validation_data['valid_customer']
        
        self.authenticate_user(valid_customer)
        
        # Should not be able to pay cancelled installment
        url = reverse('pay_installment', kwargs={'installment_id': cancelled_installment.id})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_customer_without_email_handling(self):
        """Test handling of customers without email"""
        no_email_customer = self.validation_data['no_email_customer']
        
        self.authenticate_user(no_email_customer)
        
        url = reverse('paymentplan-list')
        response = self.client.get(url)
        
        # Should return empty results for customer without email
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 0)