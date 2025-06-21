from datetime import date
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
import logging
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction

try:
    import numpy_financial as npf
except ImportError:
    raise ImportError("numpy_financial is required for payment calculations. Install with: pip install numpy-financial")

from .models import Installment

logger = logging.getLogger(__name__)

def calculate_pmt(principal, annual_rate, periods, tenor_type='month'):
    """Calculate payment including principal and interest using PMT formula"""
    try:
        # Input validation
        if not isinstance(principal, (int, float, Decimal)) or principal <= 0:
            raise ValidationError("Principal must be a positive number")
        
        if not isinstance(annual_rate, (int, float, Decimal)) or annual_rate < 0 or annual_rate > 100:
            raise ValidationError("Annual rate must be between 0 and 100")
        
        if not isinstance(periods, int) or periods <= 0:
            raise ValidationError("Periods must be a positive integer")
        
        if tenor_type not in ['month', 'week', 'day']:
            raise ValidationError("Tenor type must be 'month', 'week', or 'day'")
        
        # Convert to Decimal for precision
        principal = Decimal(str(principal))
        annual_rate = Decimal(str(annual_rate))
        
        # Handle zero interest rate
        if annual_rate == 0:
            return (principal / Decimal(periods)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        # Calculate periods per year
        periods_mapping = {'month': 12, 'week': 52, 'day': 360}
        periods_per_year = Decimal(periods_mapping[tenor_type])
        
        # Calculate rate per period
        rate = annual_rate / Decimal(100) / periods_per_year
        
        # Use numpy_financial for PMT calculation
        pmt = npf.pmt(float(rate), periods, -float(principal))
        
        if not pmt or pmt != pmt:  # Check for NaN
            raise ValidationError("Unable to calculate payment amount")
        
        result = Decimal(str(pmt)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        if result <= 0:
            raise ValidationError("Calculated payment amount is invalid")
        
        return result
        
    except (InvalidOperation, ValueError, TypeError) as e:
        logger.error(f"Error calculating PMT: {e}")
        raise ValidationError(f"Payment calculation error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error in calculate_pmt: {e}")
        raise ValidationError("An unexpected error occurred during payment calculation")

def calculate_amortization(principal, annual_rate, periods, tenor_type='month'):
    """Generate amortization schedule with principal/interest breakdown"""
    try:
        # Input validation
        if not isinstance(principal, (int, float, Decimal)) or principal <= 0:
            raise ValidationError("Principal must be a positive number")
        
        if not isinstance(annual_rate, (int, float, Decimal)) or annual_rate < 0 or annual_rate > 100:
            raise ValidationError("Annual rate must be between 0 and 100")
        
        if not isinstance(periods, int) or periods <= 0:
            raise ValidationError("Periods must be a positive integer")
        
        if tenor_type not in ['month', 'week', 'day']:
            raise ValidationError("Tenor type must be 'month', 'week', or 'day'")
        
        # Convert to Decimal for precision
        principal = Decimal(str(principal))
        annual_rate = Decimal(str(annual_rate))
        
        # Handle zero interest rate
        if annual_rate == 0:
            installment = (principal / Decimal(periods)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            return [(installment, installment, Decimal('0.00')) for _ in range(periods)]
        
        # Calculate periods per year
        periods_mapping = {'month': 12, 'week': 52, 'day': 360}
        periods_per_year = Decimal(periods_mapping[tenor_type])
        
        # Calculate rate per period
        rate = annual_rate / Decimal(100) / periods_per_year
        rate_float = float(rate)
        remaining_principal = float(principal)
        schedule = []
        
        # Use consistent PMT calculation
        pmt_amount = float(calculate_pmt(principal, annual_rate, periods, tenor_type))
        
        for period in range(1, periods + 1):
            try:
                # Calculate interest component
                interest_amount = remaining_principal * rate_float
                
                # Calculate principal component
                principal_component_float = pmt_amount - interest_amount
                
                # Handle final period adjustment to ensure total principal equals original
                if period == periods:
                    # Adjust final principal to match remaining balance
                    principal_component_float = remaining_principal
                    total_pmt_float = principal_component_float + interest_amount
                else:
                    total_pmt_float = pmt_amount
                
                # Convert to Decimal and round
                interest = Decimal(str(interest_amount)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                principal_component = Decimal(str(principal_component_float)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                total_pmt = Decimal(str(total_pmt_float)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                
                # Validate amounts
                if interest < 0:
                    interest = Decimal('0.00')
                if principal_component <= 0:
                    raise ValidationError(f"Invalid principal component for period {period}")
                
                schedule.append((total_pmt, principal_component, interest))
                remaining_principal -= float(principal_component)
                
                # Ensure remaining principal doesn't go negative (except for final period)
                if remaining_principal < -0.01 and period < periods:
                    logger.warning(f"Remaining principal went negative: {remaining_principal}")
                    remaining_principal = 0
                    
            except (ValueError, TypeError, InvalidOperation) as e:
                logger.error(f"Error calculating amortization for period {period}: {e}")
                raise ValidationError(f"Amortization calculation failed for period {period}")
        
        # Validate schedule integrity
        total_principal = sum(payment[1] for payment in schedule)
        if abs(float(total_principal) - float(principal)) > 0.10:  # Allow small rounding differences
            logger.warning(f"Principal sum mismatch: {total_principal} vs {principal}")
        
        return schedule
        
    except ValidationError:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in calculate_amortization: {e}")
        raise ValidationError("An unexpected error occurred during amortization calculation")

def mark_overdue_installments():
    """
    Utility function to mark overdue installments as 'late'
    This function now uses the enhanced signal-based system
    """
    try:
        # Import here to avoid circular imports
        from .signals import mark_all_overdue_installments
        
        logger.info("Starting overdue installments check via utils")
        updated_count = mark_all_overdue_installments()
        
        if updated_count > 0:
            logger.info(f"Successfully marked {updated_count} installments as late via utils")
        else:
            logger.info("No overdue installments found via utils")
            
        return updated_count
        
    except Exception as e:
        logger.error(f"Error marking overdue installments via utils: {e}")
        raise ValidationError("Failed to update overdue installments")

def get_payment_plan_summary(payment_plan):
    """
    Get a summary of payment plan status
    """
    try:
        if not payment_plan:
            raise ValidationError("Payment plan is required")
        
        installments = payment_plan.installments.all()
        
        if not installments.exists():
            logger.warning(f"No installments found for payment plan {payment_plan.id}")
            return {
                'total_installments': 0,
                'paid_installments': 0,
                'pending_installments': 0,
                'late_installments': 0,
                'next_due_date': None,
            }
        
        # Get counts with error handling
        total_installments = installments.count()
        paid_installments = installments.filter(status='paid').count()
        pending_installments = installments.filter(status='pending').count()
        late_installments = installments.filter(status='late').count()
        
        # Get next due date safely
        next_pending = installments.filter(status='pending').order_by('due_date').first()
        next_due_date = next_pending.due_date if next_pending else None
        
        return {
            'total_installments': total_installments,
            'paid_installments': paid_installments,
            'pending_installments': pending_installments,
            'late_installments': late_installments,
            'next_due_date': next_due_date,
        }
        
    except Exception as e:
        logger.error(f"Error getting payment plan summary: {e}")
        raise ValidationError("Failed to generate payment plan summary")
