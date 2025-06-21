# BNPL Simulator Backend

A Django-based Buy Now Pay Later (BNPL) simulator backend that provides comprehensive payment plan management with installment calculations, JWT authentication, and financial amortization features.

## Project Overview

This is a Django-based BNPL (Buy Now Pay Later) simulator backend that provides comprehensive payment plan management with installment calculations, JWT authentication, and financial amortization features.

## Essential Development Commands

### Environment Setup
```bash
# Activate virtual environment (required for all commands)
./venv/bin/python manage.py [command]

# Or use venv activation
source venv/bin/activate
python manage.py [command]
```

### Django Management
```bash
# System checks and validation
./venv/bin/python manage.py check

# Database operations
./venv/bin/python manage.py makemigrations
./venv/bin/python manage.py migrate

# Run development server
./venv/bin/python manage.py runserver

# Create superuser
./venv/bin/python manage.py createsuperuser

# Django shell with all models loaded
./venv/bin/python manage.py shell
```

### Testing
```bash
# Run Django tests
./venv/bin/python manage.py test

# Run specific app tests
./venv/bin/python manage.py test apps.payments

# Run pytest (alternative test runner)
./venv/bin/python -m pytest

# Run tests with coverage
./venv/bin/python -m pytest --cov=apps
```

## Architecture Overview

### Core Applications Structure

**Authentication App (`apps.authentication`)**
- Custom User model with `user_type` field ("merchant" or "customer")
- JWT-based authentication using django-rest-framework-simplejwt
- Dual authentication endpoints: custom views and JWT token views
- Permission classes: `IsMerchant` for merchant-only operations

**Payments App (`apps.payments`)**
- Core BNPL functionality with financial calculations
- Models: `PaymentPlan` (master) and `Installment` (line items) with interest/principal components
- Financial utilities using numpy-financial for PMT/amortization calculations
- Automated payment reminder system via Celery tasks
- Management commands for overdue marking and reminder scheduling
- Comprehensive error handling for financial operations
- Permission classes: `IsOwnerOrMerchant`, `CanPayInstallment`

**Analytics App (`apps.analytics`)**
- Basic structure for reporting and analytics features

### Key Financial Features

**Amortization Calculations (`apps.payments.utils`)**
- `calculate_pmt()`: Payment amount calculation using PMT formula
- `calculate_amortization()`: Principal/interest breakdown per installment
- Support for monthly, weekly, and daily payment schedules
- Comprehensive input validation and error handling
- Uses Decimal arithmetic for financial precision

**Payment Plan Workflow**
1. Merchant creates payment plan via `PaymentPlanCreateSerializer`
2. System auto-generates installments with principal/interest breakdown
3. Installments track status: pending → paid/late/cancelled
4. Payment plan completion triggers status updates

### Authentication Architecture

**JWT Configuration**
- Access tokens: 1 hour lifetime
- Refresh tokens: 7 days lifetime with rotation
- Custom claims include `user_type`, `email`, `username`
- Token blacklisting enabled for logout functionality

**API Endpoints Structure**
- `/api/auth/` - Authentication endpoints
- `/api/` - Payment operations (requires authentication)
- `/api/analytics/` - Analytics endpoints

### Database Design

**User Model** (`authentication.User`)
- Extends AbstractUser with custom fields
- Required fields: `user_type` ("merchant"/"customer")
- Email-based authentication (not username)

**Payment Models**
- `PaymentPlan`: Master record with merchant, customer email, terms, interest rate, and tenor type
- `Installment`: Line items with calculated principal/interest components and payment tracking
- Added fields: `interest_rate` (default 47%), `tenor_type` (month/week/day)
- Enhanced installment tracking: `principal_component`, `interest_component` fields
- Relationship: One PaymentPlan → Many Installments

### Error Handling Patterns

The codebase implements comprehensive error handling:
- **Financial calculations**: Input validation, NaN detection, precision handling
- **Payment processing**: Status validation, concurrent payment protection
- **Database operations**: Transaction safety, constraint validation
- **API responses**: Detailed error messages with appropriate HTTP status codes

### Development Dependencies

**Core Framework**
- Django 4.2.7 with DRF 3.14.0
- JWT authentication via djangorestframework-simplejwt
- Financial calculations via numpy-financial

**Testing Stack**
- pytest 7.4.3 with pytest-django plugin
- factory-boy and faker for test data generation
- Coverage reporting available

**Background Tasks**
- Celery 5.3.4 with Redis backend configured
- Comprehensive payment reminder system with `apps/payments/tasks.py`:
  - `send_payment_reminder`: Individual installment reminders
  - `send_bulk_payment_reminders`: Batch reminders for upcoming payments
  - `send_overdue_payment_reminders`: Automated overdue handling
  - `daily_payment_reminders`: Combined daily reminder workflow
  - `generate_merchant_payment_report`: Merchant analytics reports
- Django management commands for manual task execution:
  - `mark_overdue_installments`: Mark late payments
  - `send_payment_reminders`: Send reminder notifications
  - `generate_merchant_reports`: Generate merchant reports

### Configuration Notes

**Environment Variables**
- `SECRET_KEY`: Django secret key
- `DEBUG`: Debug mode toggle
- `DEFAULT_INTEREST_RATE`: Default interest rate (47.0%)

**Important Settings**
- Custom user model: `AUTH_USER_MODEL = 'authentication.User'`
- JWT authentication as default for DRF
- CORS enabled for frontend at localhost:5173
- SQLite database for development

### Recent Updates

1. **Enhanced Payment Model** (Migration 0002): Added `interest_component` and `principal_component` to Installment model
2. **Interest Rate Support**: PaymentPlan now includes configurable `interest_rate` field (default 47%)
3. **Flexible Payment Schedules**: Added `tenor_type` field supporting monthly, weekly, and daily payments
4. **Complete Task System**: Implemented comprehensive Celery task suite for payment automation
5. **Management Commands**: Added Django commands for payment operations and reporting

### Known Issues

1. **Import Dependencies**: Ensure numpy-financial is installed for financial calculations
2. **Virtual Environment**: Always use `./venv/bin/python` or activate venv before commands
3. **Email Configuration**: Tasks use mock email sending - configure SMTP for production

### Testing and Development

**Testing Financial Functions**
When testing financial calculations, use Django setup:
```python
import django
django.setup()
from apps.payments.utils import calculate_pmt, calculate_amortization
```

**Test Data Generation**
The project includes comprehensive test data seeders:
- `apps/payments/test_data_seeder.py`: Automated test data generation
- `apps/payments/test_fixtures.py`: Test fixture definitions
- `apps/payments/test_with_seeder_examples.py`: Usage examples

**Celery Task Testing**
Test Celery tasks with:
```bash
./venv/bin/python -m pytest test_celery_reminders.py
./venv/bin/python test_overdue_marking.py
./venv/bin/python test_signals.py
```

### API Authentication

All protected endpoints require JWT tokens:
```bash
# Include in request headers
Authorization: Bearer <access_token>
```

Use `/api/auth/login/` or `/api/auth/register/` to obtain tokens.