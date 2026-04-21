from django.contrib.auth.models import User
from django.db.models import Sum, Q
from rest_framework import generics, viewsets, permissions, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import Category, Transaction
from .serializers import RegisterSerializer, UserSerializer, CategorySerializer, TransactionSerializer


# ─── Auth ─────────────────────────────────────────────────────────────────────

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]


class MeView(generics.RetrieveAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


# LoginView is just SimpleJWT's TokenObtainPairView — wired in urls.py


# ─── Categories ───────────────────────────────────────────────────────────────

class CategoryViewSet(viewsets.ModelViewSet):
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Category.objects.filter(user=self.request.user)


# ─── Transactions ─────────────────────────────────────────────────────────────

class TransactionViewSet(viewsets.ModelViewSet):
    serializer_class = TransactionSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['date', 'amount']

    def get_queryset(self):
        qs = Transaction.objects.filter(user=self.request.user)

        # ?month=2024-06  →  filter by year-month
        month = self.request.query_params.get('month')
        if month:
            try:
                year, mon = month.split('-')
                qs = qs.filter(date__year=year, date__month=mon)
            except ValueError:
                pass

        # ?type=income or ?type=expense
        tx_type = self.request.query_params.get('type')
        if tx_type in ('income', 'expense'):
            qs = qs.filter(type=tx_type)

        # ?category=3
        category = self.request.query_params.get('category')
        if category:
            qs = qs.filter(category_id=category)

        return qs


# ─── Dashboard summary ────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def monthly_summary(request):
    """
    GET /api/summary/?month=2024-06
    Returns total income, total expenses, balance, and per-category breakdown.
    """
    month = request.query_params.get('month')
    qs = Transaction.objects.filter(user=request.user)

    if month:
        try:
            year, mon = month.split('-')
            qs = qs.filter(date__year=year, date__month=mon)
        except ValueError:
            pass

    totals = qs.aggregate(
        income=Sum('amount', filter=Q(type='income')),
        expenses=Sum('amount', filter=Q(type='expense')),
    )
    income = totals['income'] or 0
    expenses = totals['expenses'] or 0

    # Per-category breakdown (expenses only)
    by_category = (
        qs.filter(type='expense')
        .values('category__id', 'category__name', 'category__color')
        .annotate(total=Sum('amount'))
        .order_by('-total')
    )

    return Response({
        'income': income,
        'expenses': expenses,
        'balance': income - expenses,
        'by_category': list(by_category),
    })