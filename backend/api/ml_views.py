"""
ML API endpoints — mount these in api/urls.py

GET  /api/ml/forecast/           → spend forecasts for next month
GET  /api/ml/anomalies/?month=   → anomalous transaction IDs for a month
POST /api/ml/suggest-category/   → suggest a category for a note string
"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def forecast_view(request):
    """
    GET /api/ml/forecast/
    Returns predicted spend per category for next month.
    Uses the last 6 months of the user's transactions.

    Response:
    {
      "forecasts": [
        {
          "category_id": 3,
          "category_name": "Groceries",
          "category_color": "#15803d",
          "predicted_amount": 284.50,
          "trend": "up",          // "up" | "down" | "stable"
          "months_used": 5
        },
        ...
      ],
      "next_month": "2026-05"
    }
    """
    try:
        from api.ml_service import forecast_spending
        forecasts = forecast_spending(request.user)
    except Exception as e:
        return Response(
            {'error': 'Forecast unavailable', 'detail': str(e)},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    from datetime import date
    today = date.today()
    nm    = today.month + 1
    ny    = today.year
    if nm > 12:
        nm -= 12
        ny += 1
    next_month = f'{ny}-{str(nm).zfill(2)}'

    return Response({'forecasts': forecasts, 'next_month': next_month})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def anomalies_view(request):
    """
    GET /api/ml/anomalies/?month=YYYY-MM
    Returns IDs of transactions flagged as anomalous for the given month.
    If no month given, returns anomalies across all transactions.

    Response:
    {
      "anomaly_ids": [12, 47, 103],
      "count": 3
    }
    """
    month = request.query_params.get('month')

    try:
        from api.ml_service import detect_anomalies
        ids = detect_anomalies(request.user, month=month)
    except Exception as e:
        return Response(
            {'error': 'Anomaly detection unavailable', 'detail': str(e)},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    return Response({'anomaly_ids': list(ids), 'count': len(ids)})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def suggest_category_view(request):
    """
    POST /api/ml/suggest-category/
    Body: { "note": "weekly groceries at tesco" }

    Response:
    {
      "suggestion": {
        "category_id": 3,
        "category_name": "Groceries",
        "confidence": 0.87
      }
    }
    or { "suggestion": null } if not enough training data.
    """
    note = request.data.get('note', '').strip()
    if not note:
        return Response(
            {'error': 'note field is required'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        from api.ml_service import suggest_category
        suggestion = suggest_category(note, request.user)
    except Exception as e:
        return Response(
            {'error': 'Suggestion unavailable', 'detail': str(e)},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    return Response({'suggestion': suggestion})