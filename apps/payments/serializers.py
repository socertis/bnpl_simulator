from rest_framework import serializers
from .models import PaymentPlan, Installment
from datetime import date, timedelta
from decimal import Decimal

class InstallmentSerializer(serializers.ModelSerializer):
    is_overdue = serializers.ReadOnlyField()
    
    class Meta:
        model = Installment
        fields = [
            'id', 'installment_number', 'amount', 'due_date', 
            'status', 'paid_date', 'is_overdue'
        ]
        read_only_fields = ['id', 'paid_date']

class PaymentPlanCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentPlan
        fields = [
            'user_email', 'total_amount', 'number_of_installments', 'start_date'
        ]
    
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
        # Set the merchant as the logged-in user
        validated_data['merchant'] = self.context['request'].user
        payment_plan = PaymentPlan.objects.create(**validated_data)
        
        # Create installments
        self._create_installments(payment_plan)
        return payment_plan
    
    def _create_installments(self, payment_plan):
        """Create equal installments for the payment plan"""
        installment_amount = payment_plan.total_amount / payment_plan.number_of_installments
        
        for i in range(payment_plan.number_of_installments):
            due_date = payment_plan.start_date + timedelta(days=30 * i)  # Monthly installments
            
            Installment.objects.create(
                payment_plan=payment_plan,
                installment_number=i + 1,
                amount=installment_amount,
                due_date=due_date
            )

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
            'installments', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'merchant', 'created_at', 'updated_at']
