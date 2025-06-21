#!/usr/bin/env python3
"""
Simple installment calculation for BNPL loan review
"""
from decimal import Decimal, ROUND_HALF_UP
import math

def calculate_pmt_simple(principal, annual_rate, periods):
    """Calculate monthly payment using PMT formula"""
    # Convert annual rate to monthly rate
    monthly_rate = annual_rate / 100 / 12
    
    if monthly_rate == 0:
        return principal / periods
    
    # PMT formula: P * [r(1+r)^n] / [(1+r)^n - 1]
    numerator = monthly_rate * (1 + monthly_rate) ** periods
    denominator = (1 + monthly_rate) ** periods - 1
    
    return principal * (numerator / denominator)

def calculate_amortization_simple(principal, annual_rate, periods):
    """Calculate amortization schedule"""
    monthly_rate = annual_rate / 100 / 12
    monthly_payment = calculate_pmt_simple(principal, annual_rate, periods)
    
    schedule = []
    remaining_balance = principal
    
    for period in range(1, periods + 1):
        # Interest for this period
        interest_payment = remaining_balance * monthly_rate
        
        # Principal payment
        principal_payment = monthly_payment - interest_payment
        
        # Handle final payment adjustment
        if period == periods:
            principal_payment = remaining_balance
            monthly_payment = principal_payment + interest_payment
        
        # Round to 2 decimal places
        interest_payment = round(interest_payment, 2)
        principal_payment = round(principal_payment, 2)
        monthly_payment_rounded = round(monthly_payment, 2)
        
        schedule.append((monthly_payment_rounded, principal_payment, interest_payment))
        remaining_balance -= principal_payment
    
    return schedule, round(calculate_pmt_simple(principal, annual_rate, periods), 2)

# Loan parameters
principal = 200000.0  # SAR
annual_rate = 47.0    # 47% annual interest rate
periods = 4           # 4 months

print('=== 200,000 SAR BNPL Loan - 4 Monthly Installments ===')
print(f'Principal: {principal:,.2f} SAR')
print(f'Annual Interest Rate: {annual_rate}%')
print(f'Monthly Interest Rate: {annual_rate/12:.4f}%')
print(f'Number of Payments: {periods} months')
print()

# Calculate schedule
schedule, monthly_payment = calculate_amortization_simple(principal, annual_rate, periods)

print(f'Standard Monthly Payment: {monthly_payment:,.2f} SAR')
print()

print('=== Amortization Schedule ===')
print('Month | Payment    | Principal  | Interest   | Remaining Balance')
print('------|------------|------------|------------|------------------')

remaining_balance = principal
total_payments = 0
total_interest = 0

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
print(f'Interest as % of Principal: {(total_interest/principal*100):.2f}%')
print(f'Effective Monthly Rate: {(annual_rate/12):.4f}%')
print(f'APR: {annual_rate:.1f}%')

print()
print('=== Key Observations ===')
print(f'• Each month, customer pays approximately {monthly_payment:,.2f} SAR')
print(f'• First month interest: {schedule[0][2]:,.2f} SAR')
print(f'• Last month interest: {schedule[-1][2]:,.2f} SAR')
print(f'• Total cost of borrowing: {total_interest:,.2f} SAR ({(total_interest/principal*100):.1f}% of loan)')