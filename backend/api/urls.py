from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .views import (
    RegisterView, MeView,
    CategoryViewSet, TransactionViewSet, 
    BudgetViewSet, RecurringTransactionViewSet,
    monthly_summary, export_csv, currency_rates,
)

router = DefaultRouter()
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'transactions', TransactionViewSet, basename='transaction')
router.register(r'budgets',      BudgetViewSet,      basename='budget')
router.register(r'recurring',    RecurringTransactionViewSet, basename='recurring')

urlpatterns = [
    # Auth
    path('auth/register/',  RegisterView.as_view(),         name='register'),
    path('auth/login/',     TokenObtainPairView.as_view(),  name='token_obtain_pair'),
    path('auth/refresh/',   TokenRefreshView.as_view(),     name='token_refresh'),
    path('auth/me/',        MeView.as_view(),               name='me'),

    # Dashboard
    path('summary/', monthly_summary,   name='monthly_summary'),
    path('export/',  export_csv,        name='export_csv'),
    path('currencies/', currency_rates,  name='currency_rates'),

    # CRUD (router handles list + detail)
    path('', include(router.urls)),
]