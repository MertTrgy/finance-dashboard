"""
correlation_service.py — Spending vs Market Correlation Analysis

Answers:
  "Does my spending go up when the market goes down?"
  "What will I probably spend next month given current market direction?"
  "Which market index correlates most with my spending?"

How it works:
  1. Fetch user's monthly expense totals for the last 12 months
  2. Fetch S&P 500 monthly returns for the same period
  3. Calculate Pearson correlation coefficient (scipy)
  4. Fit a linear regression (scikit-learn) to predict next month
  5. Return insights in plain English

Requires:
    scipy (usually installed with scikit-learn)
    yfinance
"""

from datetime import date
from decimal import Decimal


def _monthly_spending(user, months: int = 12) -> dict[str, float]:
    """
    Returns a dict of { 'YYYY-MM': total_expenses } for the last N months.
    """
    from django.db.models import Sum, Q
    from api.models import Transaction

    today     = date.today()
    spending  = {}

    for i in range(months, 0, -1):
        m = today.month - i
        y = today.year
        while m <= 0:
            m += 12
            y -= 1
        key = f'{y}-{m:02d}'
        total = Transaction.objects.filter(
            user=user, type='expense',
            date__year=y, date__month=m,
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        spending[key] = float(total)

    return spending


def spending_market_correlation(user) -> dict:
    """
    Correlates the user's monthly spending with S&P 500 monthly returns.

    Returns:
    {
        "correlation":       -0.68,
        "interpretation":    "Your spending tends to increase when the S&P 500 falls.",
        "strength":          "moderate",        # weak / moderate / strong
        "direction":         "inverse",         # positive / inverse / none
        "data_points":       9,
        "monthly_data": [
            { "month": "2025-08", "spending": 1240.50, "market_return": 2.1 },
            ...
        ],
        "prediction": {
            "next_month":        "2026-06",
            "current_mkt_return": -1.2,
            "predicted_spending": 1450.00,
            "confidence":        "low"    # low / medium / high based on |correlation|
        },
        "indices_compared": [...],   # which index had strongest correlation
        "error": null
    }
    """
    from api.market_service import get_historical
    try:
        from scipy.stats import pearsonr
        from sklearn.linear_model import LinearRegression
        import numpy as np
    except ImportError:
        return {'error': 'scipy / scikit-learn not installed', 'correlation': None}

    spending = _monthly_spending(user, months=12)
    months   = sorted(spending.keys())

    if len(months) < 4:
        return {
            'correlation': None,
            'error':       'Need at least 4 months of transactions to calculate correlation.',
            'data_points': len(months),
        }

    # Test multiple indices, pick the strongest correlation
    indices = [
        ('^GSPC', 'S&P 500'),
        ('^FTSE', 'FTSE 100'),
        ('^IXIC', 'NASDAQ'),
    ]

    best_result   = None
    best_abs_corr = -1
    indices_tried = []

    for ticker, label in indices:
        hist = get_historical(ticker, period='2y')
        hist_map = {h['date']: h['return'] for h in hist}

        # Align spending months with market data
        aligned_spending = []
        aligned_market   = []
        aligned_months   = []

        for month in months:
            if month in hist_map:
                aligned_spending.append(spending[month])
                aligned_market.append(hist_map[month])
                aligned_months.append(month)

        if len(aligned_spending) < 4:
            indices_tried.append({'ticker': ticker, 'label': label, 'correlation': None})
            continue

        try:
            corr, p_value = pearsonr(aligned_spending, aligned_market)
        except Exception:
            indices_tried.append({'ticker': ticker, 'label': label, 'correlation': None})
            continue

        abs_corr = abs(corr)
        indices_tried.append({
            'ticker':      ticker,
            'label':       label,
            'correlation': round(corr, 3),
            'p_value':     round(p_value, 3),
        })

        if abs_corr > best_abs_corr:
            best_abs_corr   = abs_corr
            best_result = {
                'ticker':           ticker,
                'label':            label,
                'correlation':      corr,
                'aligned_spending': aligned_spending,
                'aligned_market':   aligned_market,
                'aligned_months':   aligned_months,
                'hist_map':         hist_map,
            }

    if best_result is None:
        return {
            'correlation': None,
            'error':       'Could not fetch market data. Check your internet connection.',
            'data_points': len(months),
        }

    corr              = best_result['correlation']
    aligned_spending  = best_result['aligned_spending']
    aligned_market    = best_result['aligned_market']
    aligned_months    = best_result['aligned_months']
    hist_map          = best_result['hist_map']

    # Strength + direction
    abs_corr = abs(corr)
    if abs_corr >= 0.6:
        strength = 'strong'
    elif abs_corr >= 0.35:
        strength = 'moderate'
    else:
        strength = 'weak'

    direction = 'none' if abs_corr < 0.2 else ('inverse' if corr < 0 else 'positive')

    # Plain-English interpretation
    idx_name = best_result['label']
    if direction == 'inverse':
        interpretation = (
            f"Your spending tends to increase when the {idx_name} falls, "
            f"and decrease when it rises ({strength} inverse relationship)."
        )
    elif direction == 'positive':
        interpretation = (
            f"Your spending tends to rise along with the {idx_name} "
            f"({strength} positive relationship)."
        )
    else:
        interpretation = (
            f"No significant relationship found between your spending and {idx_name}. "
            "Your spending appears independent of market movements."
        )

    # Linear regression for prediction
    X   = np.array(aligned_market).reshape(-1, 1)
    y   = np.array(aligned_spending)
    reg = LinearRegression()
    reg.fit(X, y)

    # Current month's market return so far
    today = date.today()
    this_month = f'{today.year}-{today.month:02d}'
    current_mkt_return = hist_map.get(this_month, 0.0)

    predicted = float(reg.predict([[current_mkt_return]])[0])
    predicted = max(predicted, 0)

    next_month_date = date(today.year + (1 if today.month == 12 else 0),
                           1 if today.month == 12 else today.month + 1, 1)
    next_month = f'{next_month_date.year}-{next_month_date.month:02d}'

    confidence = 'high' if abs_corr >= 0.6 else 'medium' if abs_corr >= 0.35 else 'low'

    # Monthly data for the chart
    monthly_data = [
        {
            'month':         aligned_months[i],
            'spending':      round(aligned_spending[i], 2),
            'market_return': round(aligned_market[i], 2),
        }
        for i in range(len(aligned_months))
    ]

    return {
        'correlation':      round(corr, 3),
        'interpretation':   interpretation,
        'strength':         strength,
        'direction':        direction,
        'data_points':      len(aligned_months),
        'best_index':       best_result['label'],
        'monthly_data':     monthly_data,
        'prediction': {
            'next_month':          next_month,
            'current_mkt_return':  round(current_mkt_return, 2),
            'predicted_spending':  round(predicted, 2),
            'confidence':          confidence,
        },
        'indices_compared': indices_tried,
        'error':            None,
    }
