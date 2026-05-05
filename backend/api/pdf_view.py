"""
GET /api/export-pdf/?month=2026-04
Returns a downloadable PDF report for the given month.
"""

from django.http import HttpResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def export_pdf(request):
    from datetime import date

    month = request.query_params.get('month')
    if not month:
        today = date.today()
        month = f"{today.year}-{str(today.month).zfill(2)}"

    try:
        from api.pdf_service import generate_monthly_pdf
        pdf_bytes = generate_monthly_pdf(request.user, month)
    except ImportError:
        return Response(
            {'error': 'reportlab not installed. Run: pip install reportlab'},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    filename = f'finance-report-{month}.pdf'
    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response