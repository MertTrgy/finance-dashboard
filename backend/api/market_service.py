"""
market_service.py — Fixed version

Key fixes:
  1. get_historical_price() — more robust date handling, explicit error logging
  2. get_live_quote()       — individual ticker lookup (more reliable than batch)
  3. get_portfolio_quotes() — falls back to individual lookups if batch fails
"""

import time
import logging

logger = logging.getLogger(__name__)

_cache: dict = {}
CACHE_TTL = 300  # 5 minutes


def _cached(key: str, fn):
    now = time.time()
    if key in _cache:
        value, expires = _cache[key]
        if now < expires:
            return value
    value = fn()
    _cache[key] = (value, now + CACHE_TTL)
    return value


def clear_cache(key_prefix: str = None):
    """Call this when the user clicks Refresh to force new data."""
    global _cache
    if key_prefix:
        _cache = {k: v for k, v in _cache.items() if not k.startswith(key_prefix)}
    else:
        _cache = {}


INDICES = [
    {'ticker': '^FTSE',  'label': 'FTSE 100'},
    {'ticker': '^GSPC',  'label': 'S&P 500'},
    {'ticker': '^IXIC',  'label': 'NASDAQ'},
    {'ticker': '^DJI',   'label': 'Dow Jones'},
]


# ── Historical price (fixed) ──────────────────────────────────────────────────

def get_historical_price(ticker: str, date_str: str) -> dict | None:
    """
    Fetch the split-adjusted closing price on or after date_str.

    Uses auto_adjust=True so all historical prices are expressed in
    terms of current share equivalents after all splits.

    Example:
        AMZN on 2022-04-01:
          Raw close:       ~$3,070
          After 20:1 split: ~$153   ← this is what we return
          split_factor = 20, so adjusted_quantity = original_quantity × 20

    Returns:
        { price, actual_date, currency, adjusted: True }
        or None on failure
    """
    import yfinance as yf
    from datetime import datetime, timedelta

    try:
        date     = datetime.strptime(date_str.strip(), '%Y-%m-%d')
        end_date = date + timedelta(days=10)  # allow up to 10 days forward for holidays

        ticker_obj = yf.Ticker(ticker)
        hist = ticker_obj.history(
            start      = date.strftime('%Y-%m-%d'),
            end        = end_date.strftime('%Y-%m-%d'),
            auto_adjust= True,   # retroactively adjusts for all splits
            actions    = False,
        )

        if hist.empty:
            logger.warning(f"No history for {ticker} from {date_str} to {end_date.strftime('%Y-%m-%d')}")
            return None

        price       = float(hist['Close'].iloc[0])
        actual_date = hist.index[0].strftime('%Y-%m-%d')

        # Get currency
        try:
            currency = ticker_obj.fast_info.currency or 'USD'
        except Exception:
            currency = 'USD'

        logger.info(f"Historical price for {ticker} on {actual_date}: {price} {currency} (split-adjusted)")
        return {
            'price':       round(price, 4),
            'actual_date': actual_date,
            'currency':    currency,
            'adjusted':    True,
        }

    except Exception as e:
        logger.error(f"get_historical_price failed for {ticker} on {date_str}: {e}")
        return None


# ── Split factor (fixed) ──────────────────────────────────────────────────────

def get_split_factor(ticker: str, since_date_str: str) -> dict:
    """
    Total share multiplier from all splits since the buy date.

    AMZN since 2022-04-01 → factor=20 (20:1 split on 2022-06-06)
    AAPL since 2020-01-01 → factor=4  (4:1 split on 2020-08-31)
    TSLA since 2024-01-01 → factor=1  (no splits after that)
    """
    import yfinance as yf

    try:
        t      = yf.Ticker(ticker)
        splits = t.splits

        if splits is None or splits.empty:
            return {'factor': 1, 'splits': []}

        # Normalise date string
        since_date_str = since_date_str.strip()
        splits_since   = splits[splits.index >= since_date_str]

        if splits_since.empty:
            return {'factor': 1, 'splits': []}

        factor     = 1.0
        split_list = []
        for date, ratio in splits_since.items():
            factor *= float(ratio)
            split_list.append({
                'date':  date.strftime('%Y-%m-%d'),
                'ratio': float(ratio),
            })

        return {'factor': round(factor, 6), 'splits': split_list}

    except Exception as e:
        logger.error(f"get_split_factor failed for {ticker} since {since_date_str}: {e}")
        return {'factor': 1, 'splits': []}


# ── Live quote — individual (more reliable) ───────────────────────────────────

def get_live_quote(ticker: str) -> dict:
    """
    Fetch live price for a single ticker using fast_info.
    More reliable than batch download for portfolio use.
    """
    def fetch():
        import yfinance as yf
        try:
            t         = yf.Ticker(ticker)
            info      = t.fast_info
            price     = float(info.last_price     or 0)
            prev      = float(info.previous_close or price)
            change    = price - prev
            change_pct= (change / prev * 100) if prev else 0
            currency  = getattr(info, 'currency', 'USD') or 'USD'

            # Try to get company name
            name = ticker
            try:
                tinfo = t.info
                name  = tinfo.get('longName') or tinfo.get('shortName') or ticker
            except Exception:
                pass

            return {
                'ticker':     ticker,
                'name':       name,
                'price':      round(price, 4),
                'change':     round(change, 4),
                'change_pct': round(change_pct, 2),
                'currency':   currency,
            }
        except Exception as e:
            logger.error(f"get_live_quote failed for {ticker}: {e}")
            return {
                'ticker': ticker, 'name': ticker,
                'price': 0, 'change': 0,
                'change_pct': 0, 'currency': 'USD',
                'error': str(e),
            }

    return _cached(f'live_{ticker}', fetch)


def get_portfolio_quotes(tickers: list[str]) -> dict[str, dict]:
    """
    Get live quotes for multiple tickers.
    Calls each ticker individually for reliability.
    """
    if not tickers:
        return {}
    return {t: get_live_quote(t) for t in tickers}


# ── Market overview ────────────────────────────────────────────────────────────

def get_market_overview() -> list[dict]:
    def fetch():
        results = []
        for idx in INDICES:
            q = get_live_quote(idx['ticker'])
            results.append({**q, 'label': idx['label']})
        return results
    return _cached('market_overview', fetch)


def get_stock_quote(ticker: str) -> dict:
    return get_live_quote(ticker)


def get_market_news(ticker: str = '^GSPC', limit: int = 6) -> list[dict]:
    def fetch():
        import yfinance as yf
        try:
            t     = yf.Ticker(ticker)
            items = t.news or []
            if not items:
                items = yf.Ticker('^GSPC').news or []
            result = []
            for item in items[:limit]:
                content  = item.get('content', {})
                title    = content.get('title', '') if isinstance(content, dict) else item.get('title', '')
                summary  = content.get('summary', '') if isinstance(content, dict) else ''
                pub_date = content.get('pubDate', '') if isinstance(content, dict) else ''
                link     = ''
                if isinstance(content, dict):
                    cn   = content.get('canonicalUrl', {})
                    link = cn.get('url', '') if isinstance(cn, dict) else ''
                if not title:
                    continue
                result.append({
                    'title':     title,
                    'summary':   summary[:200] if summary else '',
                    'url':       link,
                    'published': str(pub_date)[:10] if pub_date else '',
                    'source':    'Yahoo Finance',
                })
            return result
        except Exception:
            return []
    return _cached(f'news_{ticker}_{limit}', fetch)


def get_historical(ticker: str, period: str = '12mo') -> list[dict]:
    def fetch():
        import yfinance as yf
        try:
            hist = yf.Ticker(ticker).history(period=period, interval='1mo', auto_adjust=True)
            return [
                {
                    'date':   d.strftime('%Y-%m'),
                    'close':  round(float(r['Close']), 2),
                    'return': round(
                        (float(r['Close']) - float(r['Open'])) / float(r['Open']) * 100, 2
                    ) if r['Open'] else 0,
                }
                for d, r in hist.iterrows()
            ]
        except Exception:
            return []
    return _cached(f'hist_{ticker}_{period}', fetch)


def search_tickers(query: str) -> list[dict]:
    """
    Search for ticker symbols using Yahoo Finance's free search API.

    Examples:
        search_tickers("amazon")   → [{"ticker":"AMZN","name":"Amazon.com, Inc.",...}]
        search_tickers("AM")       → [AMZN, AMD, AMC, AMGN, ...]
        search_tickers("apple")    → [{"ticker":"AAPL","name":"Apple Inc.",...}]

    No API key needed — uses the same endpoint the Yahoo Finance website uses.
    Results cached for 60 seconds to avoid hammering the API while typing.
    """
    import requests

    query = query.strip()
    if not query or len(query) < 1:
        return []

    def fetch():
        try:
            resp = requests.get(
                'https://query1.finance.yahoo.com/v1/finance/search',
                params={
                    'q':                query,
                    'quotesCount':      8,
                    'newsCount':        0,
                    'enableFuzzyQuery': True,
                    'enableNavLinks':   False,
                },
                headers={
                    # Must include a User-Agent or Yahoo Finance returns 429
                    'User-Agent': (
                        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                        'AppleWebKit/537.36 (KHTML, like Gecko) '
                        'Chrome/120.0.0.0 Safari/537.36'
                    ),
                    'Accept': 'application/json',
                },
                timeout=5,
            )
            resp.raise_for_status()
            data   = resp.json()
            quotes = data.get('quotes', [])

            results = []
            for q in quotes:
                ticker = q.get('symbol', '')
                name   = q.get('longname') or q.get('shortname') or ticker
                qtype  = q.get('quoteType', '')
                exch   = q.get('exchange', '')

                # Only include tradeable instruments
                if qtype not in ('EQUITY', 'ETF', 'MUTUALFUND', 'INDEX', 'CRYPTOCURRENCY'):
                    continue
                if not ticker:
                    continue

                results.append({
                    'ticker':   ticker,
                    'name':     name,
                    'exchange': exch,
                    'type':     qtype,
                })

            return results

        except requests.Timeout:
            return []
        except Exception as e:
            logger.warning(f"Ticker search failed for '{query}': {e}")
            return []

    # Short cache — 60s is enough for autocomplete
    key = f'search_{query.lower()}'
    now = time.time()
    if key in _cache:
        value, expires = _cache[key]
        if now < expires:
            return value
    value = fetch()
    _cache[key] = (value, now + 60)
    return value