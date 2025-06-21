from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from datetime import date, timedelta
from apps.payments.models import Installment, PaymentPlan
from apps.payments.signals import mark_all_overdue_installments, get_overdue_installments_report
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Mark overdue installments as late and generate reports'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without making changes',
        )
        parser.add_argument(
            '--report-only',
            action='store_true',
            help='Generate report without updating any installments',
        )
        parser.add_argument(
            '--days-overdue',
            type=int,
            default=0,
            help='Minimum days overdue before marking as late (default: 0)',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Verbose output with detailed logging',
        )
    
    def handle(self, *args, **options):
        try:
            self.stdout.write(
                self.style.SUCCESS(f"Starting overdue installments check at {timezone.now()}")
            )
            
            # Calculate cutoff date
            days_overdue = options['days_overdue']
            cutoff_date = date.today() - timedelta(days=days_overdue)
            
            if days_overdue > 0:
                self.stdout.write(f"Checking installments overdue by at least {days_overdue} days (before {cutoff_date})")
            else:
                self.stdout.write(f"Checking all overdue installments (before {date.today()})")
            
            # Generate report first
            report = get_overdue_installments_report()
            
            if 'error' in report:
                raise CommandError(f"Error generating report: {report['error']}")
            
            self.display_report(report, options['verbose'])
            
            # Exit early if report-only mode
            if options['report_only']:
                self.stdout.write(self.style.SUCCESS("Report generated. No updates performed (report-only mode)."))
                return
            
            # Find installments to update
            overdue_query = Installment.objects.filter(
                status='pending',
                due_date__lt=cutoff_date if days_overdue > 0 else date.today()
            )
            
            overdue_count = overdue_query.count()
            
            if overdue_count == 0:
                self.stdout.write(self.style.SUCCESS("No overdue installments found."))
                return
            
            # Dry run mode
            if options['dry_run']:
                self.stdout.write(self.style.WARNING(f"DRY RUN: Would mark {overdue_count} installments as late:"))
                for installment in overdue_query:
                    days_late = (date.today() - installment.due_date).days
                    self.stdout.write(f"  - Installment {installment.id} (Plan {installment.payment_plan.id}) - {days_late} days late")
                return
            
            # Perform the update
            self.stdout.write(f"Marking {overdue_count} overdue installments as late...")
            
            updated_count = mark_all_overdue_installments()
            
            if updated_count > 0:
                self.stdout.write(
                    self.style.SUCCESS(f"Successfully marked {updated_count} installments as late")
                )
                
                # Log affected payment plans
                affected_plans = PaymentPlan.objects.filter(
                    installments__status='late',
                    installments__updated_at__gte=timezone.now() - timedelta(minutes=1)
                ).distinct()
                
                if affected_plans.exists():
                    self.stdout.write(f"Affected payment plans: {affected_plans.count()}")
                    if options['verbose']:
                        for plan in affected_plans:
                            self.stdout.write(f"  - Plan {plan.id}: {plan.user_email}")
            else:
                self.stdout.write(self.style.WARNING("No installments were updated"))
                
        except Exception as e:
            logger.error(f"Error in mark_overdue_installments command: {e}")
            raise CommandError(f"Command failed: {str(e)}")
    
    def display_report(self, report, verbose=False):
        """Display the overdue installments report"""
        self.stdout.write("\n" + "="*50)
        self.stdout.write("OVERDUE INSTALLMENTS REPORT")
        self.stdout.write("="*50)
        
        self.stdout.write(f"Report Date: {report['report_date']}")
        self.stdout.write(f"Overdue Pending: {report['overdue_pending_count']}")
        self.stdout.write(f"Already Late: {report['late_count']}")
        self.stdout.write(f"Total Overdue: {report['total_overdue']}")
        
        if verbose and report['overdue_pending_count'] > 0:
            self.stdout.write("\nDETAILED BREAKDOWN:")
            self.stdout.write("-" * 30)
            
            for installment in report['overdue_installments']:
                days_late = (date.today() - installment.due_date).days
                self.stdout.write(
                    f"Installment {installment.id}: "
                    f"Plan {installment.payment_plan.id}, "
                    f"Due: {installment.due_date}, "
                    f"Days Late: {days_late}, "
                    f"Amount: {installment.amount}"
                )
        
        if report['overdue_plans']:
            self.stdout.write(f"\nAffected Payment Plans: {len(report['overdue_plans'])}")
            if verbose:
                for plan_id, plan_data in report['overdue_plans'].items():
                    plan = plan_data['payment_plan']
                    overdue_count = len(plan_data['overdue_installments'])
                    self.stdout.write(f"  Plan {plan_id}: {overdue_count} overdue installments ({plan.user_email})")
        
        self.stdout.write("="*50 + "\n")