from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
from datetime import date, timedelta
from django.conf import settings

User = get_user_model()

class PaymentPlan(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    TENOR_TYPE_CHOICES = [
        ('month', 'Monthly'),
        ('week', 'Weekly'),
        ('day', 'Daily'),
    ]
    
    merchant = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='merchant_plans'
    )
    user_email = models.EmailField()
    total_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    number_of_installments = models.PositiveIntegerField(
        validators=[MinValueValidator(1)]
    )
    start_date = models.DateField()
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='active'
    )
    tenor_type = models.CharField(
        max_length=10,
        choices=TENOR_TYPE_CHOICES,
        default='month'
    )
    interest_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        default=settings.DEFAULT_INTEREST_RATE
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Payment Plan'
        verbose_name_plural = 'Payment Plans'
    
    def __str__(self):
        return f"Plan {self.id} - {self.user_email} - {self.total_amount} SAR"
    
    @property
    def installment_amount(self):
        """Calculate installment amount using PMT formula with error handling"""
        try:
            from .utils import calculate_pmt
            return calculate_pmt(
                self.total_amount,
                float(self.interest_rate),
                self.number_of_installments,
                self.tenor_type
            )
        except Exception:
            # Return a fallback calculation if PMT fails
            return self.total_amount / self.number_of_installments
    
    @property
    def paid_installments_count(self):
        """Count of paid installments"""
        return self.installments.filter(status='paid').count()
    
    @property
    def remaining_amount(self):
        """Calculate remaining amount to be paid with error handling"""
        try:
            paid_installments = self.installments.filter(status='paid')
            if not paid_installments.exists():
                return self.total_amount
            
            paid_amount = sum(installment.amount for installment in paid_installments)
            remaining = self.total_amount - paid_amount
            
            # Ensure remaining amount is not negative
            return max(Decimal('0.00'), remaining)
        except Exception:
            return self.total_amount

class Installment(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('late', 'Late'),
        ('cancelled', 'Cancelled'),
    ]
    
    payment_plan = models.ForeignKey(
        PaymentPlan, 
        on_delete=models.CASCADE, 
        related_name='installments'
    )
    installment_number = models.PositiveIntegerField()
    amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    due_date = models.DateField()
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='pending'
    )
    paid_date = models.DateTimeField(null=True, blank=True)
    principal_component = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        default=0
    )
    interest_component = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        default=0
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['installment_number']
        unique_together = ['payment_plan', 'installment_number']
        verbose_name = 'Installment'
        verbose_name_plural = 'Installments'
    
    def __str__(self):
        return f"Installment {self.installment_number} - {self.amount} SAR"
    
    @property
    def is_overdue(self):
        """Check if installment is overdue"""
        return (self.status == 'pending' and 
                self.due_date < date.today())
    
    def mark_as_late_if_overdue(self):
        """Mark installment as late if overdue with validation"""
        try:
            if self.is_overdue and self.status == 'pending':
                self.status = 'late'
                self.save(update_fields=['status', 'updated_at'])
                return True
            return False
        except Exception as e:
            from django.core.exceptions import ValidationError
            raise ValidationError(f"Failed to mark installment as late: {str(e)}")
