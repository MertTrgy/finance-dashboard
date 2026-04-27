"""
Thin wrapper around the Frankfurter exchange rate API.
https://www.frankfurter.app — free, no API key required, updated daily.

Usage:
    from api.currency_service import convert_to_gbp, get_rates

    gbp_amount, rate = convert_to_gbp(100, 'USD')   # (74.32, 0.7432)
    rates = get_rates()                              # {'USD': 1.27, 'EUR': 1.17, ...}
"""

import requests
from decimal import Decimal

FRANKFURTER_URL = 'https://api.frankfurter.app'
BASE_CURRENCY   = 'GBP'
REQUEST_TIMEOUT = 5  # seconds

# Common currencies shown in the UI
SUPPORTED_CURRENCIES = [
    'GBP', 'USD', 'EUR', 'JPY', 'CAD', 'AUD', 'CHF',
    'CNY', 'INR', 'MXN', 'BRL', 'SEK', 'NOK', 'DKK',
    'PLN', 'CZK', 'HUF', 'RON', 'TRY', 'SGD', 'HKD',
]


def get_rates(base: str = BASE_CURRENCY) -> dict:
    """
    Fetch all exchange rates with `base` as the source currency.
    Returns a dict like {'USD': 1.27, 'EUR': 1.17, ...}
    Returns an empty dict on network failure so the app degrades gracefully.
    """
    try:
        resp = requests.get(
            f'{FRANKFURTER_URL}/latest',
            params={'from': base},
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get('rates', {})
    except Exception:
        return {}


def convert_to_gbp(amount: float | Decimal, from_currency: str) -> tuple[Decimal, Decimal | None]:
    """
    Convert `amount` in `from_currency` to GBP.
    Returns (gbp_amount, exchange_rate).
    If `from_currency` is already GBP, returns (amount, None) without an API call.
    If the API call fails, returns (amount, None) — caller should handle gracefully.
    """
    amount = Decimal(str(amount))

    if from_currency.upper() == BASE_CURRENCY:
        return amount, None

    rates = get_rates(base=from_currency)
    rate  = rates.get(BASE_CURRENCY)

    if rate is None:
        # API failed or unknown currency — return unconverted
        return amount, None

    rate       = Decimal(str(rate))
    gbp_amount = (amount * rate).quantize(Decimal('0.01'))
    return gbp_amount, rate
