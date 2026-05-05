import csv

from django.contrib.auth.models import User
from django.db.models import Sum, Q
from django.http import HttpResponse
from rest_framework import generics, viewsets, permissions, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework import status

from .models import Category, Transaction, Budget, RecurringTransaction
from .pagination import TransactionPagination
from .serializers import (
    RegisterSerializer, UserSerializer,
    CategorySerializer, TransactionSerializer, 
    BudgetSerializer, RecurringTransactionSerializer,
)
from .currency_service import get_rates, SUPPORTED_CURRENCIES
from datetime import date


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
    """
    Full CRUD for transactions with search, date filtering, and pagination.

    Query params supported:
        ?month=2026-04           filter by year-month (existing)
        ?type=expense            filter by type (existing)
        ?category=3              filter by category ID (existing)
        ?search=tesco            search note AND category name (NEW)
        ?date_from=2026-04-01    filter from date inclusive (NEW)
        ?date_to=2026-04-30      filter to date inclusive (NEW)
        ?page=2                  page number (NEW)
        ?page_size=20            results per page (NEW)
    """
    serializer_class   = TransactionSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class   = TransactionPagination
    filter_backends    = [filters.OrderingFilter]
    ordering_fields    = ['date', 'amount', 'created_at']
    ordering           = ['-date', '-created_at']

    def get_queryset(self):
        qs = Transaction.objects.filter(user=self.request.user).select_related('category')

        # ── Existing filters ──────────────────────────────────────────────
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

        # ── New: text search across note + category name ──────────────────
        search = self.request.query_params.get('search', '').strip()
        if search:
            qs = qs.filter(
                Q(note__icontains=search) |
                Q(category__name__icontains=search)
            )

        # ── New: date range ───────────────────────────────────────────────
        date_from = self.request.query_params.get('date_from')
        if date_from:
            try:
                qs = qs.filter(date__gte=date_from)
            except ValueError:
                pass

        date_to = self.request.query_params.get('date_to')
        if date_to:
            try:
                qs = qs.filter(date__lte=date_to)
            except ValueError:
                pass

        return qs


# ── Recurring Transactions ────────────────────────────────────────────────────

class RecurringTransactionViewSet(viewsets.ModelViewSet):
    serializer_class   = RecurringTransactionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return RecurringTransaction.objects.filter(user=self.request.user)


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

    by_category = list(
        qs.filter(type='expense')
        .values('category__id', 'category__name', 'category__color')
        .annotate(total=Sum('amount'))
        .order_by('-total')
    )

    over_budget = []
    if month:
        for budget in Budget.objects.filter(user=request.user, month=month):
            cat_spend = next(
                (c['total'] for c in by_category if c['category__id'] == budget.category_id), 0
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
    writer.writerow(['Date', 'Type', 'Amount (GBP)', 'Original Amount',
                     'Original Currency', 'Exchange Rate', 'Category', 'Note'])

    for tx in qs:
        writer.writerow([
            tx.date, tx.type, tx.amount,
            tx.original_amount or '',
            tx.original_currency or 'GBP',
            tx.exchange_rate or '',
            tx.category.name if tx.category else '',
            tx.note,
        ])

    return response


# ── Currency rates ────────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def currency_rates(request):
    """
    GET /api/currencies/
    Returns live exchange rates (GBP base) and the list of supported currencies.
    Cached implicitly by the Frankfurter CDN — at most one real HTTP call per day.
    """
    rates = get_rates(base='GBP')
    return Response({
        'base':       'GBP',
        'rates':      rates,
        'currencies': SUPPORTED_CURRENCIES,
    })

# ── ML: Spend forecast ────────────────────────────────────────────────────────
 
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def forecast_view(request):
    try:
        from .ml_service import forecast_spending
        forecasts = forecast_spending(request.user)
    except Exception as e:
        return Response({'error': 'Forecast unavailable', 'detail': str(e)},
                        status=status.HTTP_503_SERVICE_UNAVAILABLE)
 
    today = date.today()
    nm    = today.month + 1
    ny    = today.year
    if nm > 12:
        nm -= 12
        ny += 1
    return Response({
        'forecasts':   forecasts,
        'next_month':  f'{ny}-{str(nm).zfill(2)}',
    })
 
 
# ── ML: Anomaly detection ─────────────────────────────────────────────────────
 
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def anomalies_view(request):
    month = request.query_params.get('month')
    try:
        from .ml_service import detect_anomalies
        ids = detect_anomalies(request.user, month=month)
    except Exception as e:
        return Response({'error': 'Anomaly detection unavailable', 'detail': str(e)},
                        status=status.HTTP_503_SERVICE_UNAVAILABLE)
    return Response({'anomaly_ids': list(ids), 'count': len(ids)})
 
 
# ── ML: Category suggestion ───────────────────────────────────────────────────
 
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def suggest_category_view(request):
    note = request.data.get('note', '').strip()
    if not note:
        return Response({'error': 'note field is required'},
                        status=status.HTTP_400_BAD_REQUEST)
    try:
        from .ml_service import suggest_category
        suggestion = suggest_category(note, request.user)
    except Exception as e:
        return Response({'error': 'Suggestion unavailable', 'detail': str(e)},
                        status=status.HTTP_503_SERVICE_UNAVAILABLE)
    return Response({'suggestion': suggestion})
