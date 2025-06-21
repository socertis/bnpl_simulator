#!/usr/bin/env python3
"""
Corrected installment calculation with 0.47% annual rate
"""

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

print('=== COMPARISON: 200,000 SAR BNPL Loan - 4 Monthly Installments ===')
print()

# Case 1: Current rate (47% annual)
principal = 200000.0
annual_rate_high = 47.0
periods = 4

print('CASE 1: With 47% Annual Interest Rate')
print('=' * 50)
schedule_high, payment_high = calculate_amortization_simple(principal, annual_rate_high, periods)
total_interest_high = sum(item[2] for item in schedule_high)
print(f'Monthly Payment: {payment_high:,.2f} SAR')
print(f'Total Interest: {total_interest_high:,.2f} SAR')
print(f'Total Amount Paid: {sum(item[0] for item in schedule_high):,.2f} SAR')
print()

# Case 2: Corrected rate (0.47% annual)
annual_rate_low = 0.47

print('CASE 2: With 0.47% Annual Interest Rate')
print('=' * 50)
schedule_low, payment_low = calculate_amortization_simple(principal, annual_rate_low, periods)
total_interest_low = sum(item[2] for item in schedule_low)
print(f'Monthly Payment: {payment_low:,.2f} SAR')
print(f'Total Interest: {total_interest_low:,.2f} SAR')
print(f'Total Amount Paid: {sum(item[0] for item in schedule_low):,.2f} SAR')
print()

print('DETAILED BREAKDOWN - 0.47% Annual Rate:')
print('Month | Payment    | Principal  | Interest   | Remaining Balance')
print('------|------------|------------|------------|------------------')

remaining_balance = principal
for i, (payment, principal_comp, interest_comp) in enumerate(schedule_low, 1):
    remaining_balance -= principal_comp
    print(f'{i:5d} | {payment:10,.2f} | {principal_comp:10,.2f} | {interest_comp:10,.2f} | {remaining_balance:16,.2f}')

print()
print('=== COMPARISON SUMMARY ===')
print(f'Difference in monthly payment: {payment_high - payment_low:,.2f} SAR')
print(f'Difference in total interest: {total_interest_high - total_interest_low:,.2f} SAR')
print(f'Interest savings with 0.47% rate: {((total_interest_high - total_interest_low)/total_interest_high)*100:.1f}%')