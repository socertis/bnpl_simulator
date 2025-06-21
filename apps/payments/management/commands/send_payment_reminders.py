from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from datetime import date, timedelta
from apps.payments.tasks import (
    send_bulk_payment_reminders,
    send_overdue_payment_reminders,
    daily_payment_reminders,
    send_payment_reminder
)
from apps.payments.models import Installment
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Send payment reminders using Celery tasks'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--days-ahead',
            type=int,
            default=3,
            help='Days ahead to send reminders for (default: 3)',
        )
        parser.add_argument(
            '--overdue-only',
            action='store_true',
            help='Send only overdue payment reminders',
        )
        parser.add_argument(
            '--daily-batch',
            action='store_true',
            help='Run the full daily reminder batch (3-day, 1-day, due today, overdue)',
        )
        parser.add_argument(
            '--installment-id',
            type=int,
            help='Send reminder for a specific installment ID',
        )
        parser.add_argument(
            '--async',
            action='store_true',
            help='Run tasks asynchronously (requires Celery worker)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be sent without actually sending',
        )
    
    def handle(self, *args, **options):
        try:
            self.stdout.write(
                self.style.SUCCESS(f"Starting payment reminders at {timezone.now()}")
            )
            
            # Handle specific installment reminder
            if options['installment_id']:
                return self.send_single_reminder(options)
            
            # Handle daily batch
            if options['daily_batch']:
                return self.send_daily_batch(options)
            
            # Handle overdue only
            if options['overdue_only']:
                return self.send_overdue_reminders(options)
            
            # Handle days-ahead reminders
            return self.send_days_ahead_reminders(options)
                
        except Exception as e:
            logger.error(f"Error in send_payment_reminders command: {e}")
            raise CommandError(f"Command failed: {str(e)}")
    
    def send_single_reminder(self, options):
        """Send reminder for a specific installment"""
        installment_id = options['installment_id']
        
        try:
            installment = Installment.objects.get(id=installment_id)
            days_until_due = (installment.due_date - date.today()).days
            
            self.stdout.write(f"Sending reminder for installment {installment_id}")
            self.stdout.write(f"Due date: {installment.due_date} ({days_until_due} days)")
            self.stdout.write(f"Status: {installment.status}")
            self.stdout.write(f"Amount: {installment.amount} SAR")
            
            if options['dry_run']:
                self.stdout.write(self.style.WARNING("DRY RUN: No reminder sent"))
                return
            
            if options['async']:
                task = send_payment_reminder.delay(installment_id, days_until_due)
                self.stdout.write(f"Task queued: {task.id}")
            else:
                result = send_payment_reminder(installment_id, days_until_due)
                self.stdout.write(f"Result: {result}")
                
        except Installment.DoesNotExist:
            raise CommandError(f"Installment {installment_id} not found")
    
    def send_daily_batch(self, options):
        """Send the full daily batch of reminders"""
        self.stdout.write("Running daily payment reminders batch...")
        
        if options['dry_run']:
            # Simulate what would be sent
            days_list = [3, 1, 0]  # 3-day, 1-day, due today
            total_count = 0
            
            for days in days_list:
                target_date = date.today() + timedelta(days=days)
                count = Installment.objects.filter(
                    due_date=target_date,
                    status__in=['pending', 'late']
                ).count()
                total_count += count
                self.stdout.write(f"  {days}-day reminders: {count} installments")
            
            # Overdue count
            overdue_count = Installment.objects.filter(
                status='pending',
                due_date__lt=date.today()
            ).count()
            total_count += overdue_count
            self.stdout.write(f"  Overdue reminders: {overdue_count} installments")
            
            self.stdout.write(self.style.WARNING(f"DRY RUN: Would send {total_count} total reminders"))
            return
        
        if options['async']:
            task = daily_payment_reminders.delay()
            self.stdout.write(f"Daily batch task queued: {task.id}")
        else:
            result = daily_payment_reminders()
            self.display_batch_results(result)
    
    def send_overdue_reminders(self, options):
        """Send only overdue payment reminders"""
        self.stdout.write("Sending overdue payment reminders...")
        
        if options['dry_run']:
            overdue_count = Installment.objects.filter(
                status__in=['pending', 'late'],
                due_date__lt=date.today()
            ).count()
            self.stdout.write(self.style.WARNING(f"DRY RUN: Would send {overdue_count} overdue reminders"))
            return
        
        if options['async']:
            task = send_overdue_payment_reminders.delay()
            self.stdout.write(f"Overdue reminders task queued: {task.id}")
        else:
            result = send_overdue_payment_reminders()
            self.stdout.write(f"Result: {result}")
    
    def send_days_ahead_reminders(self, options):
        """Send reminders for installments due in X days"""
        days_ahead = options['days_ahead']
        target_date = date.today() + timedelta(days=days_ahead)
        
        self.stdout.write(f"Sending reminders for installments due in {days_ahead} days ({target_date})")
        
        if options['dry_run']:
            count = Installment.objects.filter(
                due_date=target_date,
                status__in=['pending', 'late']
            ).count()
            self.stdout.write(self.style.WARNING(f"DRY RUN: Would send {count} reminders"))
            return
        
        if options['async']:
            task = send_bulk_payment_reminders.delay(days_ahead)
            self.stdout.write(f"Bulk reminders task queued: {task.id}")
        else:
            result = send_bulk_payment_reminders(days_ahead)
            self.stdout.write(f"Result: {result}")
    
    def display_batch_results(self, result):
        """Display results from daily batch execution"""
        if 'error' in result:
            self.stdout.write(self.style.ERROR(f"Batch failed: {result['error']}"))
            return
        
        self.stdout.write(self.style.SUCCESS(f"Daily batch completed: {result['total_reminders_sent']} total reminders"))
        
        details = result.get('details', {})
        for reminder_type, data in details.items():
            count = data.get('reminders_sent', 0) or data.get('overdue_reminders_sent', 0)
            self.stdout.write(f"  {reminder_type}: {count} reminders")
        
        self.stdout.write(f"Execution date: {result['execution_date']}")