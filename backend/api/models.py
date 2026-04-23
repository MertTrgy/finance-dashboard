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
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f'{self.type} £{self.amount} on {self.date}'
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