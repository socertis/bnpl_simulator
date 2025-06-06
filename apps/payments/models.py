from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from decimal import Decimal
from datetime import date, timedelta

User = get_user_model()

class PaymentPlan(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
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
        """Calculate equal installment amount"""
        return self.total_amount / self.number_of_installments
    
    @property
    def paid_installments_count(self):
        """Count of paid installments"""
        return self.installments.filter(status='paid').count()
    
    @property
    def remaining_amount(self):
        """Calculate remaining amount to be paid"""
        paid_amount = sum(
            installment.amount for installment in 
            self.installments.filter(status='paid')
        )
        return self.total_amount - paid_amount

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
        """Mark installment as late if overdue"""
        if self.is_overdue:
            self.status = 'late'
            self.save()