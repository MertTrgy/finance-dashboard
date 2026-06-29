"""
Fixed portfolio views.

The critical bug was in cost basis calculation:
  WRONG: cost_basis = buy_price x original_quantity
    e.g. $153 x 1 = $153  ← shows wrong cost

  CORRECT: cost_basis = buy_price × adjusted_quantity
    e.g. $153 x 20 = $3,060  ← correct (20:1 split)

Why: buy_price stored is already split-adjusted (e.g. $153 for AMZN not $3,070).
     adjusted_quantity = shares you now hold after splits (e.g. 20).
     So multiplying them gives what you'd have paid in today's per-share terms.
"""

import logging
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status, serializers

logger = logging.getLogger(__name__)


# ── Serializer ────────────────────────────────────────────────────────────────

class StockHoldingSerializer(serializers.ModelSerializer):
    class Meta:
        from api.models import StockHolding
        model  = StockHolding
        fields = (
            'id', 'ticker', 'name', 'quantity',
            'buy_price', 'buy_date',
            'split_factor', 'adjusted_quantity',
            'original_currency', 'created_at',
        )
        read_only_fields = ('created_at',)

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


# ── Refresh endpoint ───────────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def portfolio_refresh(request):
    """
    POST /api/portfolio/refresh/
    Clears the yfinance cache so the next GET fetches fresh prices.
    Returns updated portfolio with latest prices.
    """
    from api.market_service import clear_cache
    clear_cache('live_')           # clear all live quote caches
    clear_cache('market_overview') # clear market overview cache
    return portfolio(request._request)   # return fresh data


# ── Historical price preview ──────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def historical_price_lookup(request):
    """
    GET /api/market/historical-price/?ticker=AMZN&date=2022-04-01

    Preview endpoint — call this when user types a date to show
    them the price before they save the holding.
    """
    ticker   = request.query_params.get('ticker', '').strip().upper()
    date_str = request.query_params.get('date', '').strip()

    if not ticker or not date_str:
        return Response({'error': 'ticker and date are required'}, status=400)

    from api.market_service import get_historical_price, get_split_factor

    price_data = get_historical_price(ticker, date_str)
    if not price_data:
        return Response(
            {'error': f'No trading data found for {ticker} on {date_str}. '
                      'The market may have been closed, or the date may be before '
                      'this stock was listed. Try the next business day.'},
            status=404,
        )

    split_data = get_split_factor(ticker, date_str)

    return Response({
        'ticker':         ticker,
        'requested_date': date_str,
        'actual_date':    price_data['actual_date'],
        'buy_price':      price_data['price'],        # split-adjusted close price
        'currency':       price_data['currency'],
        'split_factor':   split_data['factor'],       # multiply original qty by this
        'splits':         split_data['splits'],
        'note': (
            f"Price is split-adjusted. {len(split_data['splits'])} split(s) found since {date_str}. "
            f"Each original share is now worth {split_data['factor']} shares."
        ) if split_data['splits'] else f"No stock splits found since {date_str}.",
    })


# ── Portfolio CRUD ────────────────────────────────────────────────────────────

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def portfolio(request):
    """
    GET  /api/portfolio/  — list holdings with live prices
    POST /api/portfolio/  — add a holding (auto-fetches buy price if buy_date provided)
    """
    from api.models import StockHolding

    # ── POST: add holding ─────────────────────────────────────────────────
    if request.method == 'POST':
        ticker    = request.data.get('ticker', '').strip().upper()
        buy_date  = request.data.get('buy_date', '').strip()
        buy_price = request.data.get('buy_price', None)
        quantity  = request.data.get('quantity', None)

        if not ticker:
            return Response({'error': 'ticker is required'}, status=400)
        if not quantity or float(quantity) <= 0:
            return Response({'error': 'quantity must be greater than 0'}, status=400)

        quantity = float(quantity)

        # Look up company name and currency
        from api.market_service import get_live_quote, get_historical_price, get_split_factor
        live      = get_live_quote(ticker)
        name      = live.get('name', ticker)
        currency  = live.get('currency', 'USD')

        split_factor      = 1.0
        adjusted_quantity = quantity
        splits_info       = []

        if buy_date:
            # ── Get split factor since buy date ───────────────────────────
            split_data        = get_split_factor(ticker, buy_date)
            split_factor      = split_data.get('factor', 1.0)
            splits_info       = split_data.get('splits', [])
            adjusted_quantity = round(quantity * split_factor, 6)

            # ── Auto-fetch historical buy price if not provided ───────────
            if not buy_price:
                logger.info(f"Fetching historical price for {ticker} on {buy_date}")
                hist = get_historical_price(ticker, buy_date)

                if hist:
                    buy_price = hist['price']
                    # Note: this price is ALREADY split-adjusted.
                    # e.g. AMZN on 2022-04-01 → $153 (not $3,070)
                    # This means: cost_basis = buy_price × adjusted_quantity
                    #   = $153 × 20 = $3,060 (correct!)
                    logger.info(
                        f"Got historical price for {ticker}: {buy_price} "
                        f"(split-adjusted, factor={split_factor})"
                    )
                else:
                    return Response(
                        {
                            'error': (
                                f'Could not find price data for {ticker} on {buy_date}. '
                                'This usually means the market was closed on that date. '
                                'Try the next business day, or enter the price manually.'
                            )
                        },
                        status=400,
                    )

        # ── Save holding ──────────────────────────────────────────────────
        try:
            # Handle duplicate ticker (update instead of creating duplicate)
            holding, created = StockHolding.objects.update_or_create(
                user   = request.user,
                ticker = ticker,
                defaults={
                    'name':              name,
                    'quantity':          quantity,
                    'buy_price':         float(buy_price) if buy_price else None,
                    'buy_date':          buy_date or None,
                    'split_factor':      split_factor,
                    'adjusted_quantity': adjusted_quantity,
                    'original_currency': currency,
                },
            )

            serializer    = StockHoldingSerializer(holding, context={'request': request})
            response_data = {
                **serializer.data,
                'splits_applied': splits_info,
                'message': (
                    f'{len(splits_info)} split(s) found. '
                    f'Your {quantity} share(s) became {adjusted_quantity} shares '
                    f'(×{split_factor} factor). '
                    f'Buy price stored as split-adjusted: {buy_price}.'
                ) if splits_info else (
                    f'No splits since {buy_date}. Buy price: {buy_price}.'
                ),
            }
            return Response(
                response_data,
                status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
            )

        except Exception as e:
            logger.error(f"Error saving holding for {ticker}: {e}")
            return Response({'error': str(e)}, status=400)

    # ── GET: list with live prices ────────────────────────────────────────
    holdings = list(StockHolding.objects.filter(user=request.user))
    if not holdings:
        return Response({
            'holdings': [], 'total_value': 0,
            'total_cost': 0, 'total_gain': 0, 'total_gain_pct': 0,
        })

    from api.market_service import get_portfolio_quotes
    tickers = [h.ticker for h in holdings]
    quotes  = get_portfolio_quotes(tickers)

    enriched    = []
    total_cost  = 0.0
    total_value = 0.0

    for h in holdings:
        q             = quotes.get(h.ticker, {})
        current_price = q.get('price', 0.0)

        orig_qty = float(h.quantity or 0)
        adj_qty  = float(h.adjusted_quantity or orig_qty)
        buy_p    = float(h.buy_price) if h.buy_price else None
        factor   = float(h.split_factor or 1)

        # ── Cost basis (FIXED) ────────────────────────────────────────────
        # buy_p is the split-adjusted historical price per current-equivalent share.
        # Multiplying by adj_qty gives the total equivalent cost in current terms.
        # Example: AMZN buy_p=$153, adj_qty=20 → cost=$3,060 (what 20 shares cost at $153 each)
        cost_basis    = (buy_p * adj_qty) if buy_p else 0.0

        current_value = current_price * adj_qty
        gain          = current_value - cost_basis
        gain_pct      = (gain / cost_basis * 100) if cost_basis else 0.0

        total_value += current_value
        total_cost  += cost_basis

        enriched.append({
            'id':                h.id,
            'ticker':            h.ticker,
            'name':              h.name,
            # Original purchase info
            'quantity':          orig_qty,
            'buy_date':          str(h.buy_date) if h.buy_date else None,
            'buy_price':         round(buy_p, 4) if buy_p else None,
            # After splits
            'split_factor':      factor,
            'adjusted_quantity': round(adj_qty, 4),
            # Live market data
            'current_price':     round(current_price, 4) if current_price else None,
            'change_pct':        q.get('change_pct', 0),
            # Financials
            'cost_basis':        round(cost_basis, 2) if cost_basis else None,
            'current_value':     round(current_value, 2) if current_value else None,
            'gain':              round(gain, 2) if buy_p else None,
            'gain_pct':          round(gain_pct, 2) if buy_p else None,
            'original_currency': h.original_currency or 'USD',
        })

    total_gain     = total_value - total_cost
    total_gain_pct = (total_gain / total_cost * 100) if total_cost else 0

    return Response({
        'holdings':       enriched,
        'total_value':    round(total_value, 2),
        'total_cost':     round(total_cost, 2),
        'total_gain':     round(total_gain, 2),
        'total_gain_pct': round(total_gain_pct, 2),
    })


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def portfolio_delete(request, pk):
    from api.models import StockHolding
    try:
        StockHolding.objects.get(id=pk, user=request.user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    except StockHolding.DoesNotExist:
        return Response({'error': 'Not found'}, status=404)


# ── Other market endpoints (unchanged) ────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def market_overview(request):
    try:
        from api.market_service import get_market_overview
        return Response({'indices': get_market_overview()})
    except ImportError:
        return Response({'error': 'pip install yfinance'}, status=503)
    except Exception as e:
        return Response({'error': str(e)}, status=503)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def market_news(request):
    ticker = request.query_params.get('ticker', '^GSPC')
    limit  = int(request.query_params.get('limit', 6))
    try:
        from api.market_service import get_market_news
        return Response({'news': get_market_news(ticker, limit), 'ticker': ticker})
    except Exception as e:
        return Response({'error': str(e)}, status=503)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def stock_quote(request):
    ticker = request.query_params.get('ticker', '').strip().upper()
    if not ticker:
        return Response({'error': 'ticker param required'}, status=400)
    from api.market_service import get_live_quote
    return Response(get_live_quote(ticker))


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def spending_correlation(request):
    try:
        from api.correlation_service import spending_market_correlation
        return Response(spending_market_correlation(request.user))
    except Exception as e:
        return Response({'error': str(e), 'correlation': None}, status=503)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def ticker_search(request):
    """
    GET /api/market/search/?q=amazon
    GET /api/market/search/?q=AM

    Returns ticker suggestions from Yahoo Finance search.
    Used by the autocomplete input when adding a portfolio holding.

    Response:
    {
        "results": [
            {
                "ticker":   "AMZN",
                "name":     "Amazon.com, Inc.",
                "exchange": "NMS",
                "type":     "EQUITY"
            },
            ...
        ]
    }
    """
    query = request.query_params.get('q', '').strip()

    if not query:
        return Response({'results': []})

    if len(query) > 50:
        return Response({'error': 'Query too long'}, status=400)

    try:
        from api.market_service import search_tickers
        results = search_tickers(query)
        return Response({'results': results})
    except Exception as e:
        logger.error(f"ticker_search error for '{query}': {e}")
        return Response({'results': [], 'error': str(e)})