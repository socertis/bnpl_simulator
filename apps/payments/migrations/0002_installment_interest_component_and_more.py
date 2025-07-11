# Generated by Django 4.2.7 on 2025-06-07 00:21

from decimal import Decimal
import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='installment',
            name='interest_component',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10, validators=[django.core.validators.MinValueValidator(0)]),
        ),
        migrations.AddField(
            model_name='installment',
            name='principal_component',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10, validators=[django.core.validators.MinValueValidator(Decimal('0.01'))]),
        ),
        migrations.AddField(
            model_name='paymentplan',
            name='interest_rate',
            field=models.DecimalField(decimal_places=2, default=47.0, max_digits=5, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(100)]),
        ),
        migrations.AddField(
            model_name='paymentplan',
            name='tenor_type',
            field=models.CharField(choices=[('month', 'Monthly'), ('week', 'Weekly'), ('day', 'Daily')], default='month', max_length=10),
        ),
    ]
