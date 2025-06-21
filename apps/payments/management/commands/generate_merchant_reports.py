from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.utils import timezone
from apps.payments.tasks import generate_merchant_payment_report
import logging

logger = logging.getLogger(__name__)
User = get_user_model()

class Command(BaseCommand):
    help = 'Generate payment reports for merchants using Celery tasks'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--merchant-id',
            type=int,
            help='Generate report for specific merchant ID',
        )
        parser.add_argument(
            '--merchant-email',
            type=str,
            help='Generate report for merchant by email',
        )
        parser.add_argument(
            '--all-merchants',
            action='store_true',
            help='Generate reports for all merchants',
        )
        parser.add_argument(
            '--async',
            action='store_true',
            help='Run tasks asynchronously (requires Celery worker)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what reports would be generated without creating them',
        )
    
    def handle(self, *args, **options):
        try:
            self.stdout.write(
                self.style.SUCCESS(f"Starting merchant report generation at {timezone.now()}")
            )
            
            # Handle specific merchant by ID
            if options['merchant_id']:
                return self.generate_single_report_by_id(options)
            
            # Handle specific merchant by email
            if options['merchant_email']:
                return self.generate_single_report_by_email(options)
            
            # Handle all merchants
            if options['all_merchants']:
                return self.generate_all_reports(options)
            
            # Default: show usage
            self.stdout.write(
                self.style.WARNING(
                    "Please specify --merchant-id, --merchant-email, or --all-merchants"
                )
            )
            
        except Exception as e:
            logger.error(f"Error in generate_merchant_reports command: {e}")
            raise CommandError(f"Command failed: {str(e)}")
    
    def generate_single_report_by_id(self, options):
        """Generate report for a specific merchant by ID"""
        merchant_id = options['merchant_id']
        
        try:
            merchant = User.objects.get(id=merchant_id, user_type='merchant')
            
            self.stdout.write(f"Generating report for merchant {merchant_id} ({merchant.email})")
            
            if options['dry_run']:
                self.stdout.write(self.style.WARNING("DRY RUN: No report generated"))
                return
            
            if options['async']:
                task = generate_merchant_payment_report.delay(merchant_id)
                self.stdout.write(f"Report task queued: {task.id}")
            else:
                result = generate_merchant_payment_report(merchant_id)
                self.display_report_summary(result)
                
        except User.DoesNotExist:
            raise CommandError(f"Merchant with ID {merchant_id} not found")
    
    def generate_single_report_by_email(self, options):
        """Generate report for a specific merchant by email"""
        merchant_email = options['merchant_email']
        
        try:
            merchant = User.objects.get(email=merchant_email, user_type='merchant')
            
            self.stdout.write(f"Generating report for merchant {merchant.id} ({merchant_email})")
            
            if options['dry_run']:
                self.stdout.write(self.style.WARNING("DRY RUN: No report generated"))
                return
            
            if options['async']:
                task = generate_merchant_payment_report.delay(merchant.id)
                self.stdout.write(f"Report task queued: {task.id}")
            else:
                result = generate_merchant_payment_report(merchant.id)
                self.display_report_summary(result)
                
        except User.DoesNotExist:
            raise CommandError(f"Merchant with email {merchant_email} not found")
    
    def generate_all_reports(self, options):
        """Generate reports for all merchants"""
        merchants = User.objects.filter(user_type='merchant')
        merchant_count = merchants.count()
        
        if merchant_count == 0:
            self.stdout.write(self.style.WARNING("No merchants found"))
            return
        
        self.stdout.write(f"Generating reports for {merchant_count} merchants")
        
        if options['dry_run']:
            for merchant in merchants:
                self.stdout.write(f"  Would generate report for: {merchant.email}")
            self.stdout.write(self.style.WARNING(f"DRY RUN: Would generate {merchant_count} reports"))
            return
        
        task_ids = []
        for merchant in merchants:
            if options['async']:
                task = generate_merchant_payment_report.delay(merchant.id)
                task_ids.append(task.id)
                self.stdout.write(f"  Queued report for {merchant.email}: {task.id}")
            else:
                result = generate_merchant_payment_report(merchant.id)
                if 'error' in result:
                    self.stdout.write(
                        self.style.ERROR(f"  Failed for {merchant.email}: {result['error']}")
                    )
                else:
                    self.stdout.write(
                        self.style.SUCCESS(f"  Generated report for {merchant.email}")
                    )
        
        if options['async']:
            self.stdout.write(f"All {len(task_ids)} report tasks queued")
        else:
            self.stdout.write(f"All {merchant_count} reports generated")
    
    def display_report_summary(self, result):
        """Display a summary of the generated report"""
        if 'error' in result:
            self.stdout.write(self.style.ERROR(f"Report generation failed: {result['error']}"))
            return
        
        self.stdout.write(self.style.SUCCESS("Report generated successfully!"))
        self.stdout.write(f"Merchant: {result['merchant_email']}")
        self.stdout.write(f"Report Date: {result['report_date']}")
        
        # Payment Plans Summary
        plans = result['payment_plans']
        self.stdout.write(f"\nPayment Plans:")
        self.stdout.write(f"  Total: {plans['total']}")
        self.stdout.write(f"  Active: {plans['active']}")
        self.stdout.write(f"  Completed: {plans['completed']}")
        
        # Installments Summary
        installments = result['installments']
        self.stdout.write(f"\nInstallments:")
        self.stdout.write(f"  Total: {installments['total']}")
        self.stdout.write(f"  Paid: {installments['paid']}")
        self.stdout.write(f"  Pending: {installments['pending']}")
        self.stdout.write(f"  Late: {installments['late']}")
        
        # Financial Summary
        financials = result['financials']
        self.stdout.write(f"\nFinancials:")
        self.stdout.write(f"  Total Revenue: {financials['total_revenue']:.2f} SAR")
        self.stdout.write(f"  Collected: {financials['collected_amount']:.2f} SAR")
        self.stdout.write(f"  Outstanding: {financials['outstanding_amount']:.2f} SAR")
        self.stdout.write(f"  Collection Rate: {financials['collection_rate']:.2f}%")