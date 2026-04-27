"""
Management command: process_recurring

Creates Transaction records for any active RecurringTransaction whose
next_due date is today or in the past, then advances next_due forward.

Usage:
    python manage.py process_recurring

Schedule (Railway / cron):
    0 1 * * *  python manage.py process_recurring   # runs at 01:00 UTC daily
"""

from datetime import date
from dateutil.relativedelta import relativedelta

from django.core.management.base import BaseCommand

from api.models import RecurringTransaction, Transaction
from api.currency_service import convert_to_gbp


class Command(BaseCommand):
    help = 'Create transactions for any recurring rules that are due today or overdue.'

    def handle(self, *args, **options):
        today    = date.today()
        due_rules = RecurringTransaction.objects.filter(active=True, next_due__lte=today)
        created  = 0

        for rule in due_rules:
            # Keep firing until next_due is in the future (catches up if skipped days)
            while rule.next_due <= today:
                # Convert currency if needed
                gbp_amount, rate = convert_to_gbp(rule.amount, rule.original_currency)

                Transaction.objects.create(
                    user              = rule.user,
                    category          = rule.category,
                    type              = rule.type,
                    amount            = gbp_amount,
                    original_amount   = rule.amount,
                    original_currency = rule.original_currency,
                    exchange_rate     = rate,
                    note              = rule.note or f'Recurring {rule.frequency}',
                    date              = rule.next_due,
                    recurring_source  = rule,
                )
                created += 1

                # Advance next_due
                if rule.frequency == RecurringTransaction.WEEKLY:
                    rule.next_due += relativedelta(weeks=1)
                else:  # monthly
                    rule.next_due += relativedelta(months=1)

            rule.save(update_fields=['next_due'])

        self.stdout.write(
            self.style.SUCCESS(f'Created {created} transaction(s) from {due_rules.count()} rule(s).')
        )
