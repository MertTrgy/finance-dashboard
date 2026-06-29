from django.db import models
from django.contrib.auth.models import User


class Category(models.Model):
    INCOME = 'income'
    EXPENSE = 'expense'
    TYPE_CHOICES = [(INCOME, 'Income'), (EXPENSE, 'Expense')]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='categories')
    name = models.CharField(max_length=100)
    type = models.CharField(max_length=10, choices=TYPE_CHOICES, default=EXPENSE)
    color = models.CharField(max_length=7, default='#6366f1')  # hex color for UI

    class Meta:
        unique_together = ('user', 'name')
        ordering = ['name']

    def __str__(self):
        return f'{self.name} ({self.type})'


class Transaction(models.Model):
    INCOME = 'income'
    EXPENSE = 'expense'
    TYPE_CHOICES = [(INCOME, 'Income'), (EXPENSE, 'Expense')]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transactions')
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='transactions'
    )
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    note = models.CharField(max_length=255, blank=True)
    date = models.DateField()
    # New feature to support multi currency
    # ── Multi-currency fields ──────────────────────────────────────────────
    # original_amount / original_currency store what the user entered
    # amount is always the GBP equivalent (used for all calculations)
    original_amount   = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    original_currency = models.CharField(max_length=3, default='GBP')
    exchange_rate     = models.DecimalField(max_digits=12, decimal_places=6, null=True, blank=True)
    # ──────────────────────────────────────────────────────────────────────


    created_at = models.DateTimeField(auto_now_add=True)

    # New feature to catch recurring transactions
    # Link back to the recurring rule that created this transaction (optional)
    recurring_source = models.ForeignKey(
        'RecurringTransaction', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='generated_transactions'
    )


    class Meta:
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f'{self.type} £{self.amount} on {self.date}'
    

class ReceiptLineItem(models.Model):
    """
    A single line item extracted from a receipt photo.
    Linked to the Transaction it was saved under.
 
    Enables tracking e.g. "how many times did I buy milk this month?"
    and feeds the ML spend prediction with item-level granularity.
    """
    transaction = models.ForeignKey(
        'Transaction',
        on_delete=models.CASCADE,
        related_name='line_items',
    )
    name        = models.CharField(max_length=255)          # "Semi-skimmed Milk 2L"
    quantity    = models.DecimalField(
        max_digits=8, decimal_places=2, default=1
    )                                                        # 2.0
    unit_price  = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )                                                        # £1.80
    total_price = models.DecimalField(
        max_digits=10, decimal_places=2
    )                                                        # £3.60
    category    = models.ForeignKey(
        'Category',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='line_items',
    )
    # Raw text as Tesseract read it — useful for debugging / reprocessing
    raw_text    = models.CharField(max_length=500, blank=True)
 
    class Meta:
        ordering = ['id']
 
    def __str__(self):
        return f'{self.name} x{self.quantity} = £{self.total_price}'
 

# ── Replace StockHolding in api/models.py ────────────────────────────────────

class StockHolding(models.Model):
    """
    Portfolio position with split tracking.

    FIELDS EXPLAINED:
        quantity          original shares purchased (e.g. 1 AMZN share)
        buy_price         split-adjusted closing price on buy_date (e.g. $153 not $3,070)
        buy_date          date of purchase (e.g. 2022-04-01)
        split_factor      multiplier from all splits since buy_date (e.g. 20)
        adjusted_quantity shares owned today = quantity × split_factor (e.g. 20)
        original_currency exchange currency (USD, GBP, EUR...)

    CALCULATIONS:
        cost_basis    = buy_price × adjusted_quantity   (e.g. $153 × 20 = $3,060)
        current_value = current_price × adjusted_quantity
        gain          = current_value − cost_basis
    """
    user      = models.ForeignKey(
        'auth.User', on_delete=models.CASCADE, related_name='stock_holdings'
    )
    ticker    = models.CharField(max_length=20)
    name      = models.CharField(max_length=200, blank=True)
    quantity  = models.DecimalField(max_digits=12, decimal_places=6, default=0)
    buy_price = models.DecimalField(max_digits=14, decimal_places=6, null=True, blank=True)
    buy_date  = models.DateField(null=True, blank=True)

    split_factor      = models.DecimalField(max_digits=12, decimal_places=6, default=1)
    adjusted_quantity = models.DecimalField(max_digits=12, decimal_places=6, default=0)
    original_currency = models.CharField(max_length=3, default='USD')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'ticker')
        ordering        = ['ticker']

    def __str__(self):
        return f'{self.user} — {self.ticker}: {self.quantity} shares (×{self.split_factor} = {self.adjusted_quantity})'


# ── After updating models.py, run: ───────────────────────────────────────────
#
#   python manage.py makemigrations api
#   python manage.py migrate
#
# If you get an error about existing columns, run:
#   python manage.py migrate --run-syncdb
    
class Budget(models.Model):
    """Monthly spend limit per category per user."""
    user     = models.ForeignKey(User, on_delete=models.CASCADE, related_name='budgets')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='budgets')
    limit    = models.DecimalField(max_digits=12, decimal_places=2)
    # month stored as YYYY-MM string for simplicity
    month    = models.CharField(max_length=7)

    class Meta:
        unique_together = ('user', 'category', 'month')
        ordering = ['month', 'category__name']

    def __str__(self):
        return f'{self.user} · {self.category.name} · {self.month} · £{self.limit}'

# This is new feature model
class RecurringTransaction(models.Model):
    WEEKLY   = 'weekly'
    MONTHLY  = 'monthly'
    FREQ_CHOICES = [(WEEKLY, 'Weekly'), (MONTHLY, 'Monthly')]

    user      = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recurring_transactions')
    category  = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='recurring_transactions'
    )
    type      = models.CharField(max_length=10, choices=Transaction.TYPE_CHOICES)
    amount    = models.DecimalField(max_digits=12, decimal_places=2)
    note      = models.CharField(max_length=255, blank=True)
    frequency = models.CharField(max_length=10, choices=FREQ_CHOICES)
    # next_due: the next date this rule should fire
    next_due  = models.DateField()
    # active: soft-disable without deleting
    active    = models.BooleanField(default=True)

    # Multi-currency support on recurring rules too
    original_currency = models.CharField(max_length=3, default='GBP')

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['next_due']

    def __str__(self):
        return f'{self.frequency} {self.type} £{self.amount} — next {self.next_due}'

