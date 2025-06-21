#!/usr/bin/env python3
"""
Calculate installment breakdown for BNPL loan
"""
import numpy_financial as npf
from decimal import Decimal, ROUND_HALF_UP

def calculate_installment_breakdown(principal, annual_rate, periods, tenor_type='month'):
    """Calculate installment breakdown using the same logic as the app"""
    
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
    
    # Use numpy_financial for PMT calculation
    pmt = npf.pmt(float(rate), periods, -float(principal))
    pmt_amount = Decimal(str(pmt)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    # Generate amortization schedule
    rate_float = float(rate)
    remaining_principal = float(principal)
    schedule = []
    
    for period in range(1, periods + 1):
        # Calculate interest component
        interest_amount = remaining_principal * rate_float
        
        # Calculate principal component
        principal_component_float = float(pmt_amount) - interest_amount
        
        # Handle final period adjustment
        if period == periods:
            principal_component_float = remaining_principal
            total_pmt_float = principal_component_float + interest_amount
        else:
            total_pmt_float = float(pmt_amount)
        
        # Convert to Decimal and round
        interest = Decimal(str(interest_amount)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        principal_component = Decimal(str(principal_component_float)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        total_pmt = Decimal(str(total_pmt_float)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        schedule.append((total_pmt, principal_component, interest))
        remaining_principal -= float(principal_component)
    
    return schedule, pmt_amount

# Loan parameters
principal = 200000  # SAR
annual_rate = 47.0  # 47% annual interest rate
periods = 4         # 4 months
tenor_type = 'month'

print('=== 200,000 SAR BNPL Loan - 4 Monthly Installments ===')
print(f'Principal: {principal:,.2f} SAR')
print(f'Annual Interest Rate: {annual_rate}%')
print(f'Monthly Interest Rate: {annual_rate/12:.4f}%')
print(f'Number of Payments: {periods} months')
print()

# Calculate schedule
schedule, monthly_payment = calculate_installment_breakdown(principal, annual_rate, periods, tenor_type)

print(f'Monthly Payment: {monthly_payment:,.2f} SAR')
print()

print('=== Amortization Schedule ===')
print('Month | Payment    | Principal  | Interest   | Remaining Balance')
print('------|------------|------------|------------|------------------')

remaining_balance = Decimal(str(principal))
total_payments = Decimal('0')
total_interest = Decimal('0')

for i, (payment, principal_comp, interest_comp) in enumerate(schedule, 1):
    remaining_balance -= principal_comp
    total_payments += payment
    total_interest += interest_comp
    
    print(f'{i:5d} | {payment:10,.2f} | {principal_comp:10,.2f} | {interest_comp:10,.2f} | {remaining_balance:16,.2f}')

print('------|------------|------------|------------|------------------')
print(f'TOTAL | {total_payments:10,.2f} | {principal:10,.2f} | {total_interest:10,.2f} |')
print()

print('=== Summary ===')
print(f'Total Interest Paid: {total_interest:,.2f} SAR')
print(f'Total Amount Paid: {total_payments:,.2f} SAR')
print(f'Interest as % of Principal: {(total_interest/Decimal(str(principal))*100):.2f}%')
print(f'Effective Monthly Rate: {(annual_rate/12):.4f}%')
print(f'APR: {annual_rate:.1f}%')