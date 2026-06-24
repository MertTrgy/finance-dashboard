"""
Market endpoints:

GET  /api/market/overview/          → live indices (FTSE, S&P, NASDAQ, Dow)
GET  /api/market/news/              → recent market news headlines
GET  /api/market/quote/?ticker=AAPL → single stock quote
GET  /api/market/correlation/       → spending vs market correlation + prediction

GET  /api/portfolio/                → user's holdings with live prices
POST /api/portfolio/                → add a holding
DELETE /api/portfolio/{id}/         → remove a holding
"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework import serializers


# ── Portfolio serializer ──────────────────────────────────────────────────────

class StockHoldingSerializer(serializers.ModelSerializer):
    class Meta:
        from api.models import StockHolding
        model  = StockHolding
        fields = ('id', 'ticker', 'name', 'quantity', 'buy_price', 'buy_date', 'created_at')
        read_only_fields = ('created_at',)

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


# ── Market overview ───────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def market_overview(request):
    """
    GET /api/market/overview/
    Returns live prices for FTSE 100, S&P 500, NASDAQ, Dow Jones.
    Cached for 5 minutes.
    """
    try:
        from api.market_service import get_market_overview
        data = get_market_overview()
        return Response({'indices': data})
    except ImportError:
        return Response(
            {'error': 'yfinance not installed. Run: pip install yfinance'},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)


# ── Market news ───────────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def market_news(request):
    """
    GET /api/market/news/?ticker=^GSPC&limit=6
    Returns recent news headlines from Yahoo Finance.
    """
    ticker = request.query_params.get('ticker', '^GSPC')
    limit  = int(request.query_params.get('limit', 6))
    try:
        from api.market_service import get_market_news
        news = get_market_news(ticker, limit=limit)
        return Response({'news': news, 'ticker': ticker})
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)


# ── Single stock quote ────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def stock_quote(request):
    """
    GET /api/market/quote/?ticker=AAPL
    Returns live price, daily change, currency for a single ticker.
    """
    ticker = request.query_params.get('ticker', '').strip().upper()
    if not ticker:
        return Response({'error': 'ticker param is required'}, status=400)
    try:
        from api.market_service import get_stock_quote
        quote = get_stock_quote(ticker)
        return Response(quote)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)


# ── Correlation ───────────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def spending_correlation(request):
    """
    GET /api/market/correlation/
    Correlates user's monthly spending with major market indices.
    Returns correlation coefficient, interpretation, and spending prediction.
    """
    try:
        from api.correlation_service import spending_market_correlation
        result = spending_market_correlation(request.user)
        return Response(result)
    except Exception as e:
        return Response(
            {'error': str(e), 'correlation': None},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )


# ── Portfolio ─────────────────────────────────────────────────────────────────

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def portfolio(request):
    """
    GET  /api/portfolio/  → list all holdings with live prices + performance
    POST /api/portfolio/  → add a holding
                            Body: {ticker, quantity, buy_price, buy_date (optional)}
    """
    from api.models import StockHolding

    if request.method == 'POST':
        # Look up the name automatically
        ticker = request.data.get('ticker', '').strip().upper()
        if not ticker:
            return Response({'error': 'ticker is required'}, status=400)

        try:
            from api.market_service import get_stock_quote
            quote = get_stock_quote(ticker)
            name  = quote.get('name', ticker)
        except Exception:
            name = ticker

        data = {**request.data, 'ticker': ticker, 'name': name}
        serializer = StockHoldingSerializer(data=data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=400)

    # GET — list holdings + enrich with live prices
    holdings = StockHolding.objects.filter(user=request.user)
    if not holdings:
        return Response({'holdings': [], 'total_value': 0, 'total_gain': 0, 'total_gain_pct': 0})

    tickers = [h.ticker for h in holdings]
    try:
        from api.market_service import get_portfolio_quotes
        quotes = get_portfolio_quotes(tickers)
    except Exception:
        quotes = {}

    enriched      = []
    total_cost    = 0.0
    total_value   = 0.0

    for h in holdings:
        q            = quotes.get(h.ticker, {})
        current_price = q.get('price', 0)
        qty           = float(h.quantity)
        buy_p         = float(h.buy_price) if h.buy_price else 0

        current_value = current_price * qty
        cost_basis    = buy_p * qty
        gain          = current_value - cost_basis
        gain_pct      = (gain / cost_basis * 100) if cost_basis else 0

        total_value += current_value
        total_cost  += cost_basis

        enriched.append({
            'id':            h.id,
            'ticker':        h.ticker,
            'name':          h.name,
            'quantity':      qty,
            'buy_price':     buy_p,
            'buy_date':      str(h.buy_date) if h.buy_date else None,
            'current_price': round(current_price, 4),
            'change_pct':    q.get('change_pct', 0),
            'current_value': round(current_value, 2),
            'cost_basis':    round(cost_basis, 2),
            'gain':          round(gain, 2),
            'gain_pct':      round(gain_pct, 2),
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
    """DELETE /api/portfolio/{id}/ → remove a holding"""
    from api.models import StockHolding
    try:
        holding = StockHolding.objects.get(id=pk, user=request.user)
        holding.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    except StockHolding.DoesNotExist:
        return Response({'error': 'Not found'}, status=404)
