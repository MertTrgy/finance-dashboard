"""
market_service.py — Free market data via yfinance (no API key required)

Provides:
    get_market_overview()      → live prices for major indices
    get_stock_quote(ticker)    → single stock live quote
    get_portfolio_quotes(tickers) → batch quotes for portfolio
    get_market_news(ticker, limit) → recent news for a ticker or index
    get_historical(ticker, period) → OHLCV history for charts/correlation

All responses are cached in memory for 5 minutes to avoid rate limiting.

Install:
    pip install yfinance
"""

import time
from datetime import datetime, timedelta

# ── Simple in-memory cache ────────────────────────────────────────────────────
_cache: dict = {}
CACHE_TTL = 300  # 5 minutes


def _cached(key: str, fn):
    """Return cached value or call fn() and cache the result."""
    now = time.time()
    if key in _cache:
        value, expires = _cache[key]
        if now < expires:
            return value
    value = fn()
    _cache[key] = (value, now + CACHE_TTL)
    return value


# ── Indices we always show ────────────────────────────────────────────────────
INDICES = [
    {'ticker': '^FTSE',  'label': 'FTSE 100'},
    {'ticker': '^GSPC',  'label': 'S&P 500'},
    {'ticker': '^IXIC',  'label': 'NASDAQ'},
    {'ticker': '^DJI',   'label': 'Dow Jones'},
]

# Tickers used to fetch general market news
NEWS_TICKERS = ['^GSPC', '^FTSE']


def _fetch_quote(ticker_symbol: str) -> dict:
    """Fetch a single ticker's live data from Yahoo Finance."""
    import yfinance as yf
    t    = yf.Ticker(ticker_symbol)
    info = t.fast_info   # fast_info is quicker than .info

    try:
        price      = float(info.last_price   or 0)
        prev_close = float(info.previous_close or price)
        change     = price - prev_close
        change_pct = (change / prev_close * 100) if prev_close else 0
        return {
            'ticker':     ticker_symbol,
            'price':      round(price, 2),
            'change':     round(change, 2),
            'change_pct': round(change_pct, 2),
            'currency':   getattr(info, 'currency', 'USD'),
        }
    except Exception:
        return {
            'ticker': ticker_symbol, 'price': 0,
            'change': 0, 'change_pct': 0, 'currency': 'USD',
        }


def get_market_overview() -> list[dict]:
    """
    Returns live prices for FTSE 100, S&P 500, NASDAQ, Dow Jones.
    Cached for 5 minutes.
    """
    def fetch():
        results = []
        for idx in INDICES:
            quote  = _fetch_quote(idx['ticker'])
            results.append({**quote, 'label': idx['label']})
        return results

    return _cached('market_overview', fetch)


def get_stock_quote(ticker: str) -> dict:
    """Returns live quote for a single ticker."""
    def fetch():
        try:
            import yfinance as yf
            t    = yf.Ticker(ticker)
            info = t.fast_info
            fast = {
                'ticker':      ticker,
                'price':       round(float(info.last_price or 0), 4),
                'change':      round(float(info.last_price or 0) - float(info.previous_close or 0), 4),
                'change_pct':  0,
                'currency':    getattr(info, 'currency', 'USD'),
                'name':        ticker,
            }
            if info.previous_close:
                fast['change_pct'] = round(fast['change'] / float(info.previous_close) * 100, 2)
            # Try to get company name
            try:
                fast['name'] = t.info.get('longName') or t.info.get('shortName') or ticker
            except Exception:
                pass
            return fast
        except Exception as e:
            return {'ticker': ticker, 'price': 0, 'change': 0,
                    'change_pct': 0, 'currency': 'USD', 'name': ticker,
                    'error': str(e)}

    return _cached(f'quote_{ticker}', fetch)


def get_portfolio_quotes(tickers: list[str]) -> dict[str, dict]:
    """
    Batch-fetch quotes for a list of tickers.
    Returns a dict keyed by ticker symbol.
    """
    if not tickers:
        return {}

    def fetch():
        import yfinance as yf
        result = {}
        # yfinance can download multiple at once
        try:
            data = yf.download(
                tickers, period='2d', interval='1d',
                progress=False, auto_adjust=True, group_by='ticker',
            )
            for ticker in tickers:
                try:
                    if len(tickers) == 1:
                        closes = data['Close']
                    else:
                        closes = data['Close'][ticker]
                    closes = closes.dropna()
                    if len(closes) >= 2:
                        price      = float(closes.iloc[-1])
                        prev_close = float(closes.iloc[-2])
                        change     = price - prev_close
                        change_pct = change / prev_close * 100
                    else:
                        price = float(closes.iloc[-1]) if len(closes) else 0
                        change, change_pct = 0, 0
                    result[ticker] = {
                        'price': round(price, 4), 'change': round(change, 4),
                        'change_pct': round(change_pct, 2),
                    }
                except Exception:
                    result[ticker] = {'price': 0, 'change': 0, 'change_pct': 0}
        except Exception:
            for t in tickers:
                result[t] = {'price': 0, 'change': 0, 'change_pct': 0}
        return result

    key = 'portfolio_' + '_'.join(sorted(tickers))
    return _cached(key, fetch)


def get_market_news(ticker: str = '^GSPC', limit: int = 6) -> list[dict]:
    """
    Returns recent news articles for a ticker from Yahoo Finance.
    Falls back to S&P 500 news if the specific ticker has no news.
    """
    def fetch():
        import yfinance as yf
        try:
            t     = yf.Ticker(ticker)
            items = t.news or []
            if not items:
                t     = yf.Ticker('^GSPC')
                items = t.news or []
            result = []
            for item in items[:limit]:
                content   = item.get('content', {})
                title     = content.get('title', '') if isinstance(content, dict) else item.get('title', '')
                summary   = content.get('summary', '') if isinstance(content, dict) else item.get('summary', '')
                pub_date  = content.get('pubDate', '') if isinstance(content, dict) else item.get('providerPublishTime', '')
                link      = ''
                if isinstance(content, dict):
                    cn   = content.get('canonicalUrl', {})
                    link = cn.get('url', '') if isinstance(cn, dict) else str(cn)
                if not title:
                    continue
                result.append({
                    'title':     title,
                    'summary':   summary[:200] if summary else '',
                    'url':       link,
                    'published': str(pub_date)[:10] if pub_date else '',
                    'source':    item.get('source', {}).get('displayName', 'Yahoo Finance')
                                 if isinstance(item.get('source'), dict) else 'Yahoo Finance',
                })
            return result
        except Exception as e:
            return [{'title': f'News unavailable: {str(e)}', 'summary': '',
                     'url': '', 'published': '', 'source': ''}]

    return _cached(f'news_{ticker}_{limit}', fetch)


def get_historical(ticker: str, period: str = '12mo') -> list[dict]:
    """
    Returns monthly OHLCV data for correlation analysis.
    period: '6mo', '12mo', '2y', '5y'
    """
    def fetch():
        import yfinance as yf
        try:
            t    = yf.Ticker(ticker)
            hist = t.history(period=period, interval='1mo', auto_adjust=True)
            result = []
            for date, row in hist.iterrows():
                result.append({
                    'date':   date.strftime('%Y-%m'),
                    'open':   round(float(row['Open']),  2),
                    'close':  round(float(row['Close']), 2),
                    'return': round(
                        (float(row['Close']) - float(row['Open'])) / float(row['Open']) * 100, 2
                    ) if row['Open'] else 0,
                })
            return result
        except Exception:
            return []

    return _cached(f'hist_{ticker}_{period}', fetch)
