from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .views import (
    RegisterView, MeView,
    CategoryViewSet, TransactionViewSet, 
    BudgetViewSet, RecurringTransactionViewSet,
    monthly_summary, export_csv, currency_rates,
    forecast_view, anomalies_view, suggest_category_view
)
from .pdf_view import export_pdf
from .ai_views import ai_chat, ai_providers, ai_context
from .receipt_views import scan_receipt, save_receipt, receipt_items

from .market_views import (
        market_overview, market_news, stock_quote,
        spending_correlation, portfolio, portfolio_delete,
        historical_price_lookup, portfolio_refresh, ticker_search,  
    )

router = DefaultRouter()
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'transactions', TransactionViewSet, basename='transaction')
router.register(r'budgets',      BudgetViewSet,      basename='budget')
router.register(r'recurring',    RecurringTransactionViewSet, basename='recurring')

urlpatterns = [
    # ── Auth ──────────────────────────────────────────────────────────────
    path('auth/register/', RegisterView.as_view(),        name='register'),
    path('auth/login/',    TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/refresh/',  TokenRefreshView.as_view(),    name='token_refresh'),
    path('auth/me/',       MeView.as_view(),              name='me'),
 
    # ── Dashboard ─────────────────────────────────────────────────────────
    path('summary/',    monthly_summary, name='monthly_summary'),
    path('export/',     export_csv,      name='export_csv'),
    path('currencies/', currency_rates,  name='currency_rates'),
 
    # ── ML ────────────────────────────────────────────────────────────────
    path('ml/forecast/',          forecast_view,         name='ml_forecast'),
    path('ml/anomalies/',         anomalies_view,        name='ml_anomalies'),
    path('ml/suggest-category/',  suggest_category_view, name='ml_suggest'),
 
    # ── CRUD (router-generated) ───────────────────────────────────────────
    path('', include(router.urls)),

    # ── AI ───────────────────────────────────────────
    path('ai/chat/',      ai_chat,      name='ai_chat'),
    path('ai/providers/', ai_providers, name='ai_providers'),
    path('ai/context/',   ai_context,   name='ai_context'),

    # ── PDF Export ───────────────────────────────────────────
    path('export-pdf/', export_pdf, name='export_pdf'),

    # ── Receipt ───────────────────────────────────────────
    path('receipt/scan/',  scan_receipt,  name='receipt_scan'),
    path('receipt/save/',  save_receipt,  name='receipt_save'),
    path('receipt/items/', receipt_items, name='receipt_items'),

    # ── Market & Stock urls ───────────────────────────────────────────
    path('market/overview/',     market_overview,      name='market_overview'),
    path('market/news/',         market_news,          name='market_news'),
    path('market/quote/',        stock_quote,          name='market_quote'),
    path('market/correlation/',  spending_correlation, name='market_correlation'),
    path('portfolio/',           portfolio,            name='portfolio'),
    path('portfolio/<int:pk>/',  portfolio_delete,     name='portfolio_delete'),
    path('market/historical-price/', historical_price_lookup, name='market_hist_price'),
    path('portfolio/refresh/',        portfolio_refresh,      name='portfolio_refresh'),
    path('market/search/', ticker_search, name='market_search'),

]