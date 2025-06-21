from rest_framework import serializers
from .models import PaymentPlan, Installment
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from django.core.exceptions import ValidationError
from django.db import transaction
import logging

logger = logging.getLogger(__name__)

class InstallmentSerializer(serializers.ModelSerializer):
    is_overdue = serializers.ReadOnlyField()
    
    class Meta:
        model = Installment
        fields = [
            'id', 'installment_number', 'amount', 'due_date', 
            'status', 'paid_date', 'is_overdue',
            'principal_component', 'interest_component'
        ]
        read_only_fields = ['id', 'paid_date']

class PaymentPlanCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentPlan
        fields = [
            'user_email', 'total_amount', 'number_of_installments', 'start_date',
            'tenor_type', 'interest_rate'
        ]
    
    def validate_interest_rate(self, value):
        if value < 0 or value > 100:
            raise serializers.ValidationError("Interest rate must be between 0 and 100")
        return value
    
    def validate_total_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Total amount must be greater than 0")
        return value
    
    def validate_number_of_installments(self, value):
        if value < 1 or value > 12:  # Max 12 installments
            raise serializers.ValidationError("Number of installments must be between 1 and 12")
        return value
    
    def validate_start_date(self, value):
        if value < date.today():
            raise serializers.ValidationError("Start date cannot be in the past")
        return value
    
    def create(self, validated_data):
        try:
            with transaction.atomic():
                # Set the merchant as the logged-in user
                user = self.context['request'].user
                if not user or not hasattr(user, 'user_type') or user.user_type != 'merchant':
                    raise serializers.ValidationError("Only merchants can create payment plans")
                
                validated_data['merchant'] = user
                
                # Create payment plan
                payment_plan = PaymentPlan.objects.create(**validated_data)
                
                # Create installments with error handling
                self._create_installments(payment_plan)
                
                logger.info(f"Payment plan {payment_plan.id} created successfully")
                return payment_plan
                
        except serializers.ValidationError:
            raise
        except Exception as e:
            logger.error(f"Error creating payment plan: {e}")
            raise serializers.ValidationError("Failed to create payment plan")
    
    def _create_installments(self, payment_plan):
        """Create installments with principal/interest breakdown"""
        from .utils import calculate_amortization
        
        try:
            with transaction.atomic():
                # Calculate amortization schedule
                amortization = calculate_amortization(
                    payment_plan.total_amount,
                    float(payment_plan.interest_rate),
                    payment_plan.number_of_installments,
                    payment_plan.tenor_type
                )
                
                if not amortization:
                    raise ValidationError("Failed to generate amortization schedule")
                
                if len(amortization) != payment_plan.number_of_installments:
                    raise ValidationError("Amortization schedule length mismatch")
                
                # Calculate days per period
                days_mapping = {'month': 30, 'week': 7, 'day': 1}
                days_per_period = days_mapping.get(payment_plan.tenor_type, 30)
                
                # Create installments
                installments_created = []
                for i, (total_pmt, principal_pmt, interest_pmt) in enumerate(amortization):
                    try:
                        # Validate payment components
                        if total_pmt <= 0 or principal_pmt <= 0 or interest_pmt < 0:
                            raise ValidationError(f"Invalid payment amounts for installment {i + 1}")
                        
                        # Calculate due date
                        due_date = payment_plan.start_date + timedelta(days=days_per_period * i)
                        
                        installment = Installment.objects.create(
                            payment_plan=payment_plan,
                            installment_number=i + 1,
                            amount=total_pmt,
                            principal_component=principal_pmt,
                            interest_component=interest_pmt,
                            due_date=due_date
                        )
                        installments_created.append(installment)
                        
                    except (ValidationError, InvalidOperation) as e:
                        logger.error(f"Error creating installment {i + 1}: {e}")
                        raise serializers.ValidationError(f"Failed to create installment {i + 1}: {str(e)}")
                
                logger.info(f"Created {len(installments_created)} installments for payment plan {payment_plan.id}")
                
        except ValidationError as e:
            logger.error(f"Validation error creating installments: {e}")
            raise serializers.ValidationError(str(e))
        except Exception as e:
            logger.error(f"Unexpected error creating installments: {e}")
            raise serializers.ValidationError("Failed to create payment installments")

class PaymentPlanSerializer(serializers.ModelSerializer):
    installments = InstallmentSerializer(many=True, read_only=True)
    merchant_name = serializers.CharField(source='merchant.username', read_only=True)
    installment_amount = serializers.ReadOnlyField()
    paid_installments_count = serializers.ReadOnlyField()
    remaining_amount = serializers.ReadOnlyField()
    
    class Meta:
        model = PaymentPlan
        fields = [
            'id', 'merchant', 'merchant_name', 'user_email', 'total_amount',
            'number_of_installments', 'installment_amount', 'start_date', 
            'status', 'paid_installments_count', 'remaining_amount',
            'installments', 'created_at', 'updated_at',
            'tenor_type', 'interest_rate'
        ]
        read_only_fields = ['id', 'merchant', 'created_at', 'updated_at']
