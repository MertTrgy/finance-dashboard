import csv

from django.contrib.auth.models import User
from django.db.models import Sum, Q
from django.http import HttpResponse
from rest_framework import generics, viewsets, permissions, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import Category, Transaction, Budget
from .serializers import (
    RegisterSerializer, UserSerializer,
    CategorySerializer, TransactionSerializer, BudgetSerializer,
)


# ── Auth ──────────────────────────────────────────────────────────────────────

class RegisterView(generics.CreateAPIView):
    queryset           = User.objects.all()
    serializer_class   = RegisterSerializer
    permission_classes = [permissions.AllowAny]


class MeView(generics.RetrieveAPIView):
    serializer_class   = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


# ── Categories ────────────────────────────────────────────────────────────────

class CategoryViewSet(viewsets.ModelViewSet):
    serializer_class   = CategorySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Category.objects.filter(user=self.request.user)


# ── Transactions ──────────────────────────────────────────────────────────────

class TransactionViewSet(viewsets.ModelViewSet):
    serializer_class   = TransactionSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends    = [filters.OrderingFilter]
    ordering_fields    = ['date', 'amount']

    def get_queryset(self):
        qs = Transaction.objects.filter(user=self.request.user)

        month = self.request.query_params.get('month')
        if month:
            try:
                year, mon = month.split('-')
                qs = qs.filter(date__year=year, date__month=mon)
            except ValueError:
                pass

        tx_type = self.request.query_params.get('type')
        if tx_type in ('income', 'expense'):
            qs = qs.filter(type=tx_type)

        category = self.request.query_params.get('category')
        if category:
            qs = qs.filter(category_id=category)

        return qs


# ── Budgets ───────────────────────────────────────────────────────────────────

class BudgetViewSet(viewsets.ModelViewSet):
    serializer_class   = BudgetSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = Budget.objects.filter(user=self.request.user)
        month = self.request.query_params.get('month')
        if month:
            qs = qs.filter(month=month)
        return qs


# ── Monthly summary (with over-budget flags) ──────────────────────────────────

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def monthly_summary(request):
    """
    GET /api/summary/?month=2025-04
    Returns income, expenses, balance, per-category breakdown,
    and an over_budget list for categories that exceeded their limit.
    """
    month = request.query_params.get('month')
    qs    = Transaction.objects.filter(user=request.user)

    if month:
        try:
            year, mon = month.split('-')
            qs = qs.filter(date__year=year, date__month=mon)
        except ValueError:
            pass

    totals   = qs.aggregate(
        income   = Sum('amount', filter=Q(type='income')),
        expenses = Sum('amount', filter=Q(type='expense')),
    )
    income   = totals['income']   or 0
    expenses = totals['expenses'] or 0

    # Per-category spend
    by_category = list(
        qs.filter(type='expense')
        .values('category__id', 'category__name', 'category__color')
        .annotate(total=Sum('amount'))
        .order_by('-total')
    )

    # Over-budget detection
    over_budget = []
    if month:
        budgets = Budget.objects.filter(user=request.user, month=month)
        for budget in budgets:
            cat_spend = next(
                (c['total'] for c in by_category if c['category__id'] == budget.category_id),
                0,
            )
            if cat_spend > budget.limit:
                over_budget.append({
                    'category_id':   budget.category_id,
                    'category_name': budget.category.name,
                    'limit':         budget.limit,
                    'spent':         cat_spend,
                    'over_by':       cat_spend - budget.limit,
                })

    return Response({
        'income':      income,
        'expenses':    expenses,
        'balance':     income - expenses,
        'by_category': by_category,
        'over_budget': over_budget,
    })


# ── CSV export ────────────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def export_csv(request):
    """
    GET /api/export/?month=2025-04
    Streams transactions as a CSV file download.
    """
    month = request.query_params.get('month')
    qs    = Transaction.objects.filter(user=request.user).select_related('category')

    if month:
        try:
            year, mon = month.split('-')
            qs = qs.filter(date__year=year, date__month=mon)
        except ValueError:
            pass

    filename = f'transactions-{month or "all"}.csv'
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)
    writer.writerow(['Date', 'Type', 'Amount', 'Category', 'Note'])

    for tx in qs:
        writer.writerow([
            tx.date,
            tx.type,
            tx.amount,
            tx.category.name if tx.category else '',
            tx.note,
        ])

    return response