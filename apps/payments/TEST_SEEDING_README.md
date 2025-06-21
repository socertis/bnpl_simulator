# Test Data Seeding System

This document explains how to use the comprehensive test data seeding system for the payment app tests.

## Overview

The test data seeding system provides:
- **Consistent test data** across different test runs
- **Automatic cleanup** after each test
- **Predefined scenarios** for common testing needs
- **Easy customization** for specific test requirements
- **Isolated data** to prevent test interference

## Files Structure

```
apps/payments/
├── test_data_seeder.py          # Core seeding functionality
├── test_fixtures.py             # Predefined test scenarios and fixtures
├── test_with_seeder_examples.py # Usage examples
├── tests.py                     # Updated existing tests
└── TEST_SEEDING_README.md       # This documentation
```

## Quick Start

### 1. Basic Manual Seeding

```python
from rest_framework.test import APITestCase
from .test_data_seeder import TestDataSeeder

class MyTestCase(APITestCase):
    def setUp(self):
        self.seeder = TestDataSeeder()
        
        # Create test data
        self.merchant = self.seeder.create_merchant()
        self.customer = self.seeder.create_customer()
        self.payment_plan = self.seeder.create_payment_plan(
            merchant=self.merchant,
            customer_email=self.customer.email
        )
    
    def tearDown(self):
        self.seeder.cleanup_all()
    
    def test_something(self):
        # Your test logic here
        pass
```

### 2. Using Predefined Scenarios

```python
from .test_fixtures import CommonTestScenarios

class MyTestCase(APITestCase):
    def setUp(self):
        self.test_data = CommonTestScenarios.security_test_data()
        self.merchant = self.test_data['primary_merchant']
        self.customer = self.test_data['primary_customer']
    
    def tearDown(self):
        self.test_data['seeder'].cleanup_all()
```

### 3. Using Inheritance (Automatic Setup)

```python
from .test_data_seeder import BaseTestWithSeeder

class MyTestCase(BaseTestWithSeeder, APITestCase):
    def seed_test_data(self):
        # Define your specific test data
        self.merchant = self.seeder.create_merchant()
        self.customer = self.seeder.create_customer()
    
    def test_something(self):
        # Test data is automatically available
        # Cleanup happens automatically
        pass
```

## Available Seeding Methods

### Core Methods

#### `TestDataSeeder`

- `create_merchant(**kwargs)` - Create a merchant user
- `create_customer(**kwargs)` - Create a customer user  
- `create_payment_plan(merchant, customer_email=None, **kwargs)` - Create a payment plan
- `create_installment(payment_plan, **kwargs)` - Create an installment
- `create_test_scenario(scenario_name)` - Create predefined scenarios
- `cleanup_all()` - Clean up all created data

#### `PaymentTestFixtures`

Properties for quick access to common scenarios:
- `simple_merchant_customer` - Basic merchant-customer setup
- `multi_merchant_setup` - Multiple merchants for isolation testing
- `payment_workflow_data` - Payment workflow with mixed installment states
- `edge_cases_data` - Edge cases and error scenarios
- `isolation_test_data` - Cross-user isolation testing

Helper methods:
- `get_jwt_token(user)` - Get JWT token for authentication
- `get_auth_headers(user)` - Get authentication headers for API requests
- `create_custom_merchant(**kwargs)` - Create custom merchant
- `create_custom_customer(**kwargs)` - Create custom customer
- `create_test_installments(payment_plan, count=3, **kwargs)` - Create multiple installments

## Predefined Scenarios

### 1. Security Test Data
```python
data = CommonTestScenarios.security_test_data()
```
**Contains:**
- Primary merchant and customer
- Other merchant and customer (for isolation testing)
- Payment plans for each pair
- Installments in pending state

**Use for:** Security testing, access control, user isolation

### 2. Functional Test Data
```python
data = CommonTestScenarios.functional_test_data()
```
**Contains:**
- Merchant and customer
- Active payment plan with mixed installment statuses (pending, late, paid, future)
- Completed payment plan with all installments paid

**Use for:** Payment workflows, business logic, status transitions

### 3. Validation Test Data
```python
data = CommonTestScenarios.validation_test_data()
```
**Contains:**
- Valid merchant and customer
- Invalid user with wrong user_type
- Customer without email
- Cancelled payment plan and installments

**Use for:** Validation testing, error handling, edge cases

## Test Data Structure

### Created Objects Include:

**Users:**
- Unique usernames and emails (timestamped)
- Correct user_type (merchant/customer)
- Test passwords set to 'testpass123'

**Payment Plans:**
- Realistic financial data
- Future start dates (to avoid validation errors)
- Proper merchant-customer relationships

**Installments:**
- Calculated principal/interest components
- Proper due dates
- Various statuses (pending, late, paid, cancelled)

## Authentication Helpers

### JWT Token Generation
```python
# Using fixtures
token = fixtures.get_jwt_token(user)
headers = fixtures.get_auth_headers(user)

# Using test client
self.client.credentials(**headers)
```

### Manual Token Generation
```python
from rest_framework_simplejwt.tokens import RefreshToken

def get_jwt_token(self, user):
    refresh = RefreshToken.for_user(user)
    return str(refresh.access_token)

def authenticate_user(self, user):
    token = self.get_jwt_token(user)
    self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
```

## Best Practices

### 1. Always Clean Up
```python
def tearDown(self):
    if hasattr(self, 'seeder'):
        self.seeder.cleanup_all()
    # or for scenarios
    if hasattr(self, 'test_data') and 'seeder' in self.test_data:
        self.test_data['seeder'].cleanup_all()
```

### 2. Use Appropriate Scenarios
- **Security tests**: Use `security_test_data()`
- **Payment workflows**: Use `functional_test_data()`
- **Validation/errors**: Use `validation_test_data()`
- **Custom needs**: Use manual seeding with `TestDataSeeder`

### 3. Unique Data Generation
The seeder automatically generates unique usernames and emails to prevent conflicts:
```python
merchant1 = seeder.create_merchant()  # merchant_test_1_123456@test.com
merchant2 = seeder.create_merchant()  # merchant_test_2_123457@test.com
```

### 4. Use Real Customer Emails
When creating payment plans via API, use the actual customer's email:
```python
data = {
    'user_email': self.customer_user.email,  # ✅ Correct
    'total_amount': '1000.00',
    # ... other fields
}
# Instead of:
# 'user_email': 'customer@test.com',  # ❌ May not match
```

## Common Patterns

### Pattern 1: API Security Testing
```python
class SecurityTestCase(APITestCase):
    def setUp(self):
        self.data = CommonTestScenarios.security_test_data()
        self.primary_merchant = self.data['primary_merchant']
        self.other_merchant = self.data['other_merchant']
    
    def tearDown(self):
        self.data['seeder'].cleanup_all()
    
    def test_merchant_isolation(self):
        # Test that merchants only see their own data
        pass
```

### Pattern 2: Payment Workflow Testing
```python
class PaymentWorkflowTestCase(APITestCase):
    def setUp(self):
        self.data = CommonTestScenarios.functional_test_data()
        self.customer = self.data['customer']
        self.pending_installment = self.data['pending_installment']
    
    def test_payment_success(self):
        # Test successful payment workflow
        pass
```

### Pattern 3: Custom Scenario Creation
```python
class CustomTestCase(APITestCase):
    def setUp(self):
        self.seeder = TestDataSeeder()
        
        # Create custom scenario
        self.merchant = self.seeder.create_merchant(
            username='special_merchant',
            email='special@merchant.com'
        )
        
        self.payment_plan = self.seeder.create_payment_plan(
            merchant=self.merchant,
            total_amount=Decimal('5000.00'),
            number_of_installments=10
        )
    
    def tearDown(self):
        self.seeder.cleanup_all()
```

## Migration from Old Tests

If you have existing tests, here's how to migrate:

### Before (Manual Setup)
```python
def setUp(self):
    self.merchant = User.objects.create_user(
        username='merchant',
        email='merchant@test.com',
        user_type='merchant'
    )
    # ... more manual setup
```

### After (Using Seeder)
```python
def setUp(self):
    self.seeder = TestDataSeeder()
    self.merchant = self.seeder.create_merchant()
    # ... automatic cleanup in tearDown
```

## Troubleshooting

### Common Issues

1. **Tests failing with 403 errors**
   - Make sure you're using the actual user's email in payment plans
   - Check that the customer email matches the authenticated user

2. **Data conflicts between tests**
   - Ensure `cleanup_all()` is called in `tearDown`
   - Use unique identifiers (the seeder handles this automatically)

3. **Authentication issues**
   - Make sure to call `authenticate_user()` before API calls
   - Check that JWT tokens are properly formatted

### Debug Tips

```python
# Check what data was created
summary = self.seeder.get_summary()
print(f"Created: {summary}")

# Verify user emails match
print(f"Customer email: {self.customer.email}")
print(f"Payment plan email: {self.payment_plan.user_email}")

# Check authentication
response = self.client.get('/api/plans/')
print(f"Auth status: {response.status_code}")
```

## Examples

See `test_with_seeder_examples.py` for comprehensive examples of:
- Basic seeder usage
- Scenario-based testing
- Fixtures usage
- Inheritance patterns
- Validation testing
- Custom scenario creation

## Running Tests

```bash
# Run all payment tests
./venv/bin/python manage.py test apps.payments.tests

# Run seeder examples
./venv/bin/python manage.py test apps.payments.test_with_seeder_examples

# Run specific test class
./venv/bin/python manage.py test apps.payments.tests.PaymentPlanEndpointSecurityTestCase
```