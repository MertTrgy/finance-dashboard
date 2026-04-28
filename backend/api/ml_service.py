"""
ml_service.py — Machine learning features for Finance Dashboard

Three independent functions, each importable on its own:

1. forecast_spending(user)        → predicted spend per category next month
2. detect_anomalies(user, month)  → transaction IDs flagged as anomalous
3. suggest_category(note, user)   → best matching category name for a note string

All models are trained on-the-fly from the user's own transaction history.
No pre-trained weights, no external model files — everything lives in the DB.

Dependencies (add to requirements.txt):
    scikit-learn>=1.4
    numpy>=1.26
"""

import numpy as np
from datetime import date
from collections import defaultdict

from django.db.models import Sum

# Lazy imports so Django starts even if scikit-learn isn't installed yet
def _sklearn():
    from sklearn.linear_model import LinearRegression
    from sklearn.ensemble import IsolationForest
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.naive_bayes import MultinomialNB
    from sklearn.pipeline import Pipeline
    return LinearRegression, IsolationForest, TfidfVectorizer, MultinomialNB, Pipeline


# ── 1. Spend forecasting ──────────────────────────────────────────────────────

def forecast_spending(user, months_of_history: int = 6) -> list[dict]:
    """
    For each expense category the user has used, predict next month's spend
    using a simple linear regression over the last N months of history.

    Returns a list of dicts:
        [{ category_id, category_name, category_color,
           predicted_amount, trend, months_used }, ...]

    trend: 'up' | 'down' | 'stable'
    months_used: how many months of data were available (min 2 to predict)
    """
    from api.models import Transaction

    LinearRegression, *_ = _sklearn()

    today    = date.today()
    results  = []

    # Build a list of the last N months as YYYY-MM strings
    history_months = []
    for i in range(months_of_history, 0, -1):
        # Go back i months from today
        m = today.month - i
        y = today.year
        while m <= 0:
            m += 12
            y -= 1
        history_months.append((y, m))

    # Fetch per-category monthly totals in one query
    qs = (
        Transaction.objects
        .filter(user=user, type='expense')
        .values('category__id', 'category__name', 'category__color',
                'date__year', 'date__month')
        .annotate(total=Sum('amount'))
    )

    # Organise into { cat_id: { (year, month): total } }
    cat_data: dict[int, dict] = defaultdict(dict)
    cat_meta: dict[int, dict] = {}

    for row in qs:
        cid = row['category__id']
        cat_data[cid][(row['date__year'], row['date__month'])] = float(row['total'])
        cat_meta[cid] = {
            'category_id':    cid,
            'category_name':  row['category__name'] or 'Uncategorised',
            'category_color': row['category__color'] or '#888780',
        }

    for cid, monthly in cat_data.items():
        # Build X (month index 0..N-1) and y (spend) vectors
        X, y_vals = [], []
        for idx, (yr, mo) in enumerate(history_months):
            spend = monthly.get((yr, mo), 0.0)
            X.append([idx])
            y_vals.append(spend)

        months_with_data = sum(1 for v in y_vals if v > 0)

        # Need at least 2 months of real data to fit a line
        if months_with_data < 2:
            predicted = np.mean(y_vals) if any(v > 0 for v in y_vals) else 0.0
            trend = 'stable'
        else:
            model = LinearRegression()
            model.fit(np.array(X), np.array(y_vals))
            # Predict the next month (index = months_of_history)
            predicted = float(model.predict([[months_of_history]])[0])
            predicted = max(predicted, 0.0)  # spend can't be negative

            slope = model.coef_[0]
            if slope > 2:
                trend = 'up'
            elif slope < -2:
                trend = 'down'
            else:
                trend = 'stable'

        results.append({
            **cat_meta[cid],
            'predicted_amount': round(predicted, 2),
            'trend':            trend,
            'months_used':      months_with_data,
        })

    # Sort by predicted amount descending
    results.sort(key=lambda r: r['predicted_amount'], reverse=True)
    return results


# ── 2. Anomaly detection ──────────────────────────────────────────────────────

def detect_anomalies(user, month: str | None = None) -> set[int]:
    """
    Use IsolationForest to flag unusually large or unusual transactions.

    Trains on ALL user transactions (amount + day-of-month as features),
    then scores the transactions for the given month (or all if month=None).

    Returns a set of transaction IDs that are flagged as anomalous.
    Requires at least 10 transactions total to produce meaningful results.
    """
    from api.models import Transaction

    _, IsolationForest, *_ = _sklearn()

    all_tx = list(
        Transaction.objects.filter(user=user, type='expense')
        .values('id', 'amount', 'date')
    )

    if len(all_tx) < 10:
        return set()  # not enough data

    # Features: [amount, day_of_month]
    X_all = np.array([
        [float(t['amount']), t['date'].day]
        for t in all_tx
    ])
    ids_all = [t['id'] for t in all_tx]

    model = IsolationForest(
        contamination=0.1,   # expect ~10% anomalies
        random_state=42,
        n_estimators=100,
    )
    preds = model.fit_predict(X_all)  # -1 = anomaly, 1 = normal

    # Build set of ALL anomalous IDs
    anomaly_ids = {ids_all[i] for i, p in enumerate(preds) if p == -1}

    # If month filter requested, intersect with that month's transactions
    if month:
        try:
            yr, mo = month.split('-')
            month_ids = set(
                Transaction.objects.filter(
                    user=user, type='expense',
                    date__year=yr, date__month=mo,
                ).values_list('id', flat=True)
            )
            return anomaly_ids & month_ids
        except ValueError:
            pass

    return anomaly_ids


# ── 3. Auto-categorisation ────────────────────────────────────────────────────

def suggest_category(note: str, user) -> dict | None:
    """
    Train a TF-IDF + Naive Bayes classifier on the user's existing
    transactions that have both a note and a category.

    Returns the best matching category as:
        { category_id, category_name, confidence }
    or None if there's not enough training data (< 5 labelled examples).

    confidence: float 0..1 (probability of the top prediction)
    """
    from api.models import Transaction

    _, _, TfidfVectorizer, MultinomialNB, Pipeline = _sklearn()

    # Fetch all transactions with both a note and a category
    labelled = list(
        Transaction.objects.filter(user=user)
        .exclude(note='')
        .exclude(category__isnull=True)
        .values('note', 'category__id', 'category__name')
    )

    if len(labelled) < 5:
        return None  # not enough data to train

    texts  = [t['note'] for t in labelled]
    labels = [t['category__id'] for t in labelled]
    label_names = {t['category__id']: t['category__name'] for t in labelled}

    # Pipeline: TF-IDF vectoriser → Multinomial Naive Bayes
    pipeline = Pipeline([
        ('tfidf', TfidfVectorizer(
            lowercase=True,
            stop_words='english',
            ngram_range=(1, 2),   # unigrams + bigrams
            min_df=1,
        )),
        ('clf', MultinomialNB(alpha=1.0)),
    ])

    pipeline.fit(texts, labels)

    proba     = pipeline.predict_proba([note])[0]
    top_idx   = int(np.argmax(proba))
    top_label = pipeline.classes_[top_idx]
    confidence = float(proba[top_idx])

    return {
        'category_id':   int(top_label),
        'category_name': label_names.get(top_label, 'Unknown'),
        'confidence':    round(confidence, 3),
    }