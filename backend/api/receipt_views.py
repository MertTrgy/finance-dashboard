"""
Receipt scanning endpoints:

POST /api/receipt/scan/   → OCR + parse image, return structured data for review
POST /api/receipt/save/   → save reviewed data as Transaction + ReceiptLineItems
GET  /api/receipt/items/  → query line items (for ML tracking)
"""

import base64
from datetime import date

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from api.models import Transaction, Category, ReceiptLineItem
from api.currency_service import convert_to_gbp
from api.ml_service import suggest_category


# ── Scan ──────────────────────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def scan_receipt(request):
    """
    POST /api/receipt/scan/
    Body: { "image": "<base64 encoded image>", "mime_type": "image/jpeg" }

    Returns structured receipt data for the frontend review modal:
    {
        "merchant":  "Tesco",
        "date":      "2026-05-01",
        "currency":  "GBP",
        "total":     42.50,
        "items": [
            {
                "name":        "Semi-Skimmed Milk 2L",
                "quantity":    2,
                "unit_price":  1.80,
                "total_price": 3.60,
                "suggested_category_id":   3,
                "suggested_category_name": "Groceries",
                "suggestion_confidence":   0.87
            },
            ...
        ],
        "raw_text": "..."   // for debugging
    }
    """
    image_b64 = request.data.get('image', '')
    if not image_b64:
        return Response({'error': 'image field is required (base64)'}, status=400)

    # Decode base64
    try:
        # Strip data URL prefix if present (data:image/jpeg;base64,...)
        if ',' in image_b64:
            image_b64 = image_b64.split(',', 1)[1]
        image_bytes = base64.b64decode(image_b64)
    except Exception:
        return Response({'error': 'Invalid base64 image data'}, status=400)

    # OCR
    try:
        from api.receipt_ocr import extract_text_from_image, parse_receipt
        raw_text = extract_text_from_image(image_bytes)
    except ImportError as e:
        return Response({'error': str(e)}, status=503)
    except RuntimeError as e:
        return Response({'error': str(e)}, status=503)
    except Exception as e:
        return Response({'error': f'OCR failed: {str(e)}'}, status=500)

    # Parse
    try:
        receipt = parse_receipt(raw_text)
    except Exception as e:
        return Response({'error': f'Parsing failed: {str(e)}'}, status=500)

    # Suggest categories for each item using the ML model
    enriched_items = []
    for item in receipt['items']:
        suggestion = None
        try:
            suggestion = suggest_category(item['name'], request.user)
        except Exception:
            pass

        enriched_items.append({
            **item,
            'suggested_category_id':   suggestion['category_id']   if suggestion else None,
            'suggested_category_name': suggestion['category_name'] if suggestion else None,
            'suggestion_confidence':   suggestion['confidence']    if suggestion else None,
        })

    return Response({
        **receipt,
        'items': enriched_items,
    })


# ── Save ──────────────────────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def save_receipt(request):
    """
    POST /api/receipt/save/
    Body:
    {
        "merchant":    "Tesco",
        "date":        "2026-05-01",
        "currency":    "GBP",
        "total":       42.50,
        "note":        "Weekly shop",           // optional
        "category_id": 3,                       // optional — category for the transaction
        "items": [
            {
                "name":        "Milk 2L",
                "quantity":    2,
                "unit_price":  1.80,
                "total_price": 3.60,
                "category_id": 3,               // optional per item
                "raw_text":    "..."
            },
            ...
        ]
    }

    Creates:
    - One Transaction (type=expense, amount=total in GBP)
    - One ReceiptLineItem per item

    Returns the created Transaction.
    """
    data = request.data

    merchant    = data.get('merchant', 'Receipt')
    tx_date     = data.get('date', str(date.today()))
    currency    = data.get('currency', 'GBP').upper()
    total       = float(data.get('total', 0))
    note        = data.get('note', '') or f'{merchant} receipt'
    category_id = data.get('category_id')
    items       = data.get('items', [])

    if total <= 0:
        return Response({'error': 'total must be greater than 0'}, status=400)

    # Resolve category
    category = None
    if category_id:
        try:
            category = Category.objects.get(id=category_id, user=request.user)
        except Category.DoesNotExist:
            pass

    # Convert total to GBP if needed
    from decimal import Decimal
    total_decimal = Decimal(str(total))
    if currency != 'GBP':
        gbp_total, rate = convert_to_gbp(total_decimal, currency)
    else:
        gbp_total, rate = total_decimal, None

    # Create the main transaction
    transaction = Transaction.objects.create(
        user              = request.user,
        category          = category,
        type              = 'expense',
        amount            = gbp_total,
        original_amount   = total_decimal,
        original_currency = currency,
        exchange_rate     = rate,
        note              = note,
        date              = tx_date,
    )

    # Create line items
    for item_data in items:
        item_cat = None
        item_cat_id = item_data.get('category_id')
        if item_cat_id:
            try:
                item_cat = Category.objects.get(id=item_cat_id, user=request.user)
            except Category.DoesNotExist:
                pass

        try:
            ReceiptLineItem.objects.create(
                transaction = transaction,
                name        = item_data.get('name', 'Item')[:255],
                quantity    = Decimal(str(item_data.get('quantity', 1))),
                unit_price  = Decimal(str(item_data['unit_price'])) if item_data.get('unit_price') else None,
                total_price = Decimal(str(item_data.get('total_price', 0))),
                category    = item_cat,
                raw_text    = item_data.get('raw_text', '')[:500],
            )
        except Exception:
            pass  # Don't fail the whole transaction if one item has bad data

    # Serialize response
    from api.serializers import TransactionSerializer
    serializer = TransactionSerializer(transaction, context={'request': request})
    return Response(serializer.data, status=status.HTTP_201_CREATED)


# ── Line item history ─────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def receipt_items(request):
    """
    GET /api/receipt/items/?name=milk&month=2026-04

    Query line items across receipts — powers the "how many milks did I buy?" feature.
    Returns aggregated item history with quantities and totals.
    """
    from django.db.models import Sum, Count

    name  = request.query_params.get('name', '').strip()
    month = request.query_params.get('month', '')

    qs = ReceiptLineItem.objects.filter(transaction__user=request.user)

    if name:
        qs = qs.filter(name__icontains=name)

    if month:
        try:
            yr, mo = month.split('-')
            qs = qs.filter(transaction__date__year=yr, transaction__date__month=mo)
        except ValueError:
            pass

    # Aggregate by item name
    summary = (
        qs.values('name')
        .annotate(
            times_bought  = Count('id'),
            total_qty     = Sum('quantity'),
            total_spent   = Sum('total_price'),
        )
        .order_by('-total_spent')
    )

    return Response({
        'items': list(summary),
        'count': len(summary),
    })