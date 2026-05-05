"""
tests.py — API test suite for Finance Dashboard

Run with:
    python manage.py test api

Coverage:
    - Auth: register, login, refresh, /me
    - Categories: CRUD + ownership isolation
    - Transactions: CRUD + search + date filter + pagination
    - Budgets: CRUD + upsert
    - Summary: income/expense totals + over-budget detection
    - ML: forecast, anomalies, suggest-category (graceful degradation)
    - CSV export
    - PDF export
"""

from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from api.models import Category, Transaction, Budget, RecurringTransaction


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_user(username='testuser', password='testpass123'):
    return User.objects.create_user(username=username, password=password, email=f'{username}@test.com')


def auth_headers(user):
    """Return Authorization header dict for a given user."""
    refresh = RefreshToken.for_user(user)
    return {'HTTP_AUTHORIZATION': f'Bearer {refresh.access_token}'}


def make_category(user, name='Groceries', type='expense', color='#15803d'):
    return Category.objects.create(user=user, name=name, type=type, color=color)


def make_transaction(user, category=None, type='expense', amount='50.00',
                     note='Test transaction', date_offset=0):
    return Transaction.objects.create(
        user=user,
        category=category,
        type=type,
        amount=Decimal(amount),
        note=note,
        date=date.today() - timedelta(days=date_offset),
        original_currency='GBP',
    )


# ── Auth Tests ────────────────────────────────────────────────────────────────

class AuthTests(APITestCase):

    def test_register_creates_user(self):
        res = self.client.post('/api/auth/register/', {
            'username': 'newuser',
            'email':    'new@test.com',
            'password': 'strongpass1',
        })
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(username='newuser').exists())

    def test_register_requires_8_char_password(self):
        res = self.client.post('/api/auth/register/', {
            'username': 'u', 'email': 'u@t.com', 'password': 'short',
        })
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_returns_tokens(self):
        make_user()
        res = self.client.post('/api/auth/login/', {
            'username': 'testuser', 'password': 'testpass123',
        })
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn('access',  res.data)
        self.assertIn('refresh', res.data)

    def test_login_wrong_password_rejected(self):
        make_user()
        res = self.client.post('/api/auth/login/', {
            'username': 'testuser', 'password': 'wrong',
        })
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_me_returns_current_user(self):
        user = make_user()
        res  = self.client.get('/api/auth/me/', **auth_headers(user))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['username'], 'testuser')

    def test_me_requires_auth(self):
        res = self.client.get('/api/auth/me/')
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_token_refresh(self):
        user    = make_user()
        refresh = RefreshToken.for_user(user)
        res     = self.client.post('/api/auth/refresh/', {'refresh': str(refresh)})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn('access', res.data)


# ── Category Tests ────────────────────────────────────────────────────────────

class CategoryTests(APITestCase):

    def setUp(self):
        self.user  = make_user()
        self.other = make_user('otheruser')

    def test_create_category(self):
        res = self.client.post('/api/categories/', {
            'name': 'Rent', 'type': 'expense', 'color': '#b91c1c',
        }, **auth_headers(self.user))
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data['name'], 'Rent')

    def test_list_returns_only_own_categories(self):
        make_category(self.user,  'Mine')
        make_category(self.other, 'Theirs')
        res = self.client.get('/api/categories/', **auth_headers(self.user))
        names = [c['name'] for c in res.data]
        self.assertIn('Mine', names)
        self.assertNotIn('Theirs', names)

    def test_update_category_color(self):
        cat = make_category(self.user)
        res = self.client.patch(f'/api/categories/{cat.id}/', {'color': '#ff0000'},
                                **auth_headers(self.user))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['color'], '#ff0000')

    def test_cannot_access_other_users_category(self):
        cat = make_category(self.other)
        res = self.client.delete(f'/api/categories/{cat.id}/', **auth_headers(self.user))
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_category(self):
        cat = make_category(self.user)
        res = self.client.delete(f'/api/categories/{cat.id}/', **auth_headers(self.user))
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Category.objects.filter(id=cat.id).exists())


# ── Transaction Tests ─────────────────────────────────────────────────────────

class TransactionTests(APITestCase):

    def setUp(self):
        self.user  = make_user()
        self.cat   = make_category(self.user)
        self.other = make_user('other2')

    def test_create_transaction(self):
        res = self.client.post('/api/transactions/', {
            'type': 'expense', 'input_amount': '42.50',
            'input_currency': 'GBP', 'date': str(date.today()), 'note': 'Coffee',
        }, **auth_headers(self.user))
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data['note'], 'Coffee')

    def test_transaction_list_paginated(self):
        for i in range(25):
            make_transaction(self.user, note=f'tx{i}')
        res = self.client.get('/api/transactions/?page=1', **auth_headers(self.user))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn('count',   res.data)
        self.assertIn('results', res.data)
        self.assertLessEqual(len(res.data['results']), 20)

    def test_search_by_note(self):
        make_transaction(self.user, note='Tesco weekly shop')
        make_transaction(self.user, note='Amazon order')
        res = self.client.get('/api/transactions/?search=tesco', **auth_headers(self.user))
        notes = [t['note'] for t in res.data['results']]
        self.assertTrue(any('Tesco' in n for n in notes))
        self.assertFalse(any('Amazon' in n for n in notes))

    def test_search_by_category_name(self):
        make_transaction(self.user, category=self.cat, note='shop')
        res = self.client.get(
            f'/api/transactions/?search={self.cat.name}', **auth_headers(self.user)
        )
        self.assertGreater(len(res.data['results']), 0)

    def test_date_range_filter(self):
        make_transaction(self.user, note='old',   date_offset=10)
        make_transaction(self.user, note='recent', date_offset=0)
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        res = self.client.get(
            f'/api/transactions/?date_from={yesterday}', **auth_headers(self.user)
        )
        notes = [t['note'] for t in res.data['results']]
        self.assertIn('recent', notes)
        self.assertNotIn('old', notes)

    def test_month_filter(self):
        month = date.today().strftime('%Y-%m')
        make_transaction(self.user, note='this month')
        res = self.client.get(f'/api/transactions/?month={month}', **auth_headers(self.user))
        self.assertGreater(len(res.data['results']), 0)

    def test_edit_transaction(self):
        tx  = make_transaction(self.user, note='original')
        res = self.client.patch(f'/api/transactions/{tx.id}/', {'note': 'updated'},
                                **auth_headers(self.user))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['note'], 'updated')

    def test_delete_transaction(self):
        tx  = make_transaction(self.user)
        res = self.client.delete(f'/api/transactions/{tx.id}/', **auth_headers(self.user))
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)

    def test_cannot_see_other_users_transactions(self):
        tx  = make_transaction(self.other, note='private')
        res = self.client.get('/api/transactions/', **auth_headers(self.user))
        notes = [t['note'] for t in res.data['results']]
        self.assertNotIn('private', notes)


# ── Budget Tests ──────────────────────────────────────────────────────────────

class BudgetTests(APITestCase):

    def setUp(self):
        self.user  = make_user()
        self.cat   = make_category(self.user)
        self.month = date.today().strftime('%Y-%m')

    def test_create_budget(self):
        res = self.client.post('/api/budgets/', {
            'category': self.cat.id, 'limit': '100.00', 'month': self.month,
        }, **auth_headers(self.user))
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data['limit'], '100.00')

    def test_update_budget_limit(self):
        budget = Budget.objects.create(
            user=self.user, category=self.cat, limit=Decimal('100'), month=self.month
        )
        res = self.client.patch(f'/api/budgets/{budget.id}/', {'limit': '200.00'},
                                **auth_headers(self.user))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['limit'], '200.00')

    def test_budget_list_filtered_by_month(self):
        Budget.objects.create(user=self.user, category=self.cat, limit=100, month='2025-01')
        Budget.objects.create(user=self.user, category=self.cat, limit=200, month=self.month)
        res   = self.client.get(f'/api/budgets/?month={self.month}', **auth_headers(self.user))
        months = [b['month'] for b in res.data]
        self.assertTrue(all(m == self.month for m in months))


# ── Summary Tests ─────────────────────────────────────────────────────────────

class SummaryTests(APITestCase):

    def setUp(self):
        self.user  = make_user()
        self.cat   = make_category(self.user)
        self.month = date.today().strftime('%Y-%m')

    def test_summary_totals(self):
        make_transaction(self.user, type='income',  amount='1000.00')
        make_transaction(self.user, type='expense', amount='400.00', category=self.cat)
        res = self.client.get(f'/api/summary/?month={self.month}', **auth_headers(self.user))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(float(res.data['income']),   1000.0)
        self.assertEqual(float(res.data['expenses']),  400.0)
        self.assertEqual(float(res.data['balance']),   600.0)

    def test_over_budget_flag(self):
        Budget.objects.create(
            user=self.user, category=self.cat, limit=Decimal('50'), month=self.month
        )
        make_transaction(self.user, type='expense', amount='80.00', category=self.cat)
        res = self.client.get(f'/api/summary/?month={self.month}', **auth_headers(self.user))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data['over_budget']), 1)
        self.assertEqual(res.data['over_budget'][0]['category_name'], self.cat.name)

    def test_empty_month_returns_zeros(self):
        res = self.client.get('/api/summary/?month=2020-01', **auth_headers(self.user))
        self.assertEqual(float(res.data['income']),   0)
        self.assertEqual(float(res.data['expenses']), 0)
        self.assertEqual(float(res.data['balance']),  0)

    def test_summary_isolates_users(self):
        other = make_user('other3')
        make_transaction(other, type='income', amount='9999.00')
        res = self.client.get(f'/api/summary/?month={self.month}', **auth_headers(self.user))
        self.assertEqual(float(res.data['income']), 0)


# ── CSV Export Tests ──────────────────────────────────────────────────────────

class CSVExportTests(APITestCase):

    def setUp(self):
        self.user  = make_user()
        self.month = date.today().strftime('%Y-%m')

    def test_csv_export_returns_file(self):
        make_transaction(self.user, note='CSV test')
        res = self.client.get(f'/api/export/?month={self.month}', **auth_headers(self.user))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res['Content-Type'], 'text/csv')
        self.assertIn('attachment', res['Content-Disposition'])

    def test_csv_contains_transaction_data(self):
        make_transaction(self.user, note='CSV row test')
        res     = self.client.get(f'/api/export/?month={self.month}', **auth_headers(self.user))
        content = res.content.decode('utf-8')
        self.assertIn('CSV row test', content)
        self.assertIn('Date', content)  # header row


# ── ML Tests (graceful degradation) ──────────────────────────────────────────

class MLTests(APITestCase):
    """
    ML endpoints should return 200 even with minimal data —
    they degrade gracefully when there's not enough history.
    """

    def setUp(self):
        self.user = make_user()
        self.cat  = make_category(self.user)
        # Add some transactions for the ML to work with
        for i in range(5):
            make_transaction(self.user, category=self.cat, note=f'shop {i}', date_offset=i)

    def test_forecast_returns_200(self):
        res = self.client.get('/api/ml/forecast/', **auth_headers(self.user))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn('forecasts', res.data)

    def test_anomalies_returns_200(self):
        month = date.today().strftime('%Y-%m')
        res   = self.client.get(f'/api/ml/anomalies/?month={month}', **auth_headers(self.user))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn('anomaly_ids', res.data)

    def test_suggest_category_requires_note(self):
        res = self.client.post('/api/ml/suggest-category/', {}, **auth_headers(self.user))
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_suggest_category_returns_200_with_note(self):
        res = self.client.post('/api/ml/suggest-category/', {'note': 'weekly groceries'},
                               **auth_headers(self.user))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn('suggestion', res.data)


# ── PDF Export Tests ──────────────────────────────────────────────────────────

class PDFExportTests(APITestCase):

    def setUp(self):
        self.user  = make_user()
        self.month = date.today().strftime('%Y-%m')

    def test_pdf_export_returns_pdf(self):
        make_transaction(self.user, note='PDF test')
        res = self.client.get(f'/api/export-pdf/?month={self.month}', **auth_headers(self.user))
        # 200 if reportlab installed, 503 if not — both are acceptable
        self.assertIn(res.status_code, [200, 503])
        if res.status_code == 200:
            self.assertEqual(res['Content-Type'], 'application/pdf')

    def test_pdf_requires_auth(self):
        res = self.client.get(f'/api/export-pdf/?month={self.month}')
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)