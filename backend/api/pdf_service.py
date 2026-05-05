"""
pdf_service.py — Monthly PDF report generator

Produces a clean, professional PDF with:
  - Cover section: month, user, generated date
  - Summary cards: income, expenses, balance
  - Budget vs actual table (if budgets exist)
  - Spending by category table
  - Recent transactions table

Requirements:
    pip install reportlab
"""

from datetime import date
from decimal import Decimal
from io import BytesIO

from django.db.models import Sum, Q

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER

from api.models import Transaction, Budget, Category


def _fmt(amount) -> str:
    try:
        return f"£{float(amount):,.2f}"
    except (TypeError, ValueError):
        return "£0.00"


def generate_monthly_pdf(user, month: str) -> bytes:
    """
    Generate a PDF report for the given user and month (YYYY-MM).
    Returns raw PDF bytes ready to send as an HTTP response.
    """


    # ── Parse month ───────────────────────────────────────────────────────
    try:
        year, mon = month.split('-')
        year, mon = int(year), int(mon)
    except (ValueError, AttributeError):
        today = date.today()
        year, mon = today.year, today.month

    month_label = date(year, mon, 1).strftime('%B %Y')

    # ── Fetch data ────────────────────────────────────────────────────────
    month_qs = Transaction.objects.filter(user=user, date__year=year, date__month=mon)
    totals   = month_qs.aggregate(
        income   = Sum('amount', filter=Q(type='income')),
        expenses = Sum('amount', filter=Q(type='expense')),
    )
    income   = totals['income']   or Decimal('0')
    expenses = totals['expenses'] or Decimal('0')
    balance  = income - expenses

    by_category = list(
        month_qs.filter(type='expense')
        .values('category__name', 'category__color')
        .annotate(total=Sum('amount'))
        .order_by('-total')
    )

    budgets   = list(Budget.objects.filter(user=user, month=month).select_related('category'))
    recent_tx = list(month_qs.select_related('category').order_by('-date', '-created_at')[:20])

    # ── PDF setup ─────────────────────────────────────────────────────────
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        rightMargin=20*mm, leftMargin=20*mm,
        topMargin=20*mm, bottomMargin=20*mm,
    )

    # Colour palette
    DARK    = colors.HexColor('#1a1a1a')
    MID     = colors.HexColor('#6b7280')
    LIGHT   = colors.HexColor('#f5f4f0')
    GREEN   = colors.HexColor('#15803d')
    RED     = colors.HexColor('#b91c1c')
    BLUE    = colors.HexColor('#1d4ed8')
    BORDER  = colors.HexColor('#e2e0da')
    WHITE   = colors.white

    styles  = getSampleStyleSheet()
    story   = []

    # ── Custom styles ─────────────────────────────────────────────────────
    def style(name, **kw):
        return ParagraphStyle(name, **kw)

    h1   = style('H1',  fontName='Helvetica-Bold', fontSize=28, textColor=DARK,   spaceAfter=2)
    h2   = style('H2',  fontName='Helvetica-Bold', fontSize=14, textColor=DARK,   spaceBefore=14, spaceAfter=4)
    sub  = style('Sub', fontName='Helvetica',       fontSize=10, textColor=MID,    spaceAfter=2)
    body = style('Bod', fontName='Helvetica',       fontSize=9,  textColor=DARK,   leading=13)
    mono = style('Mon', fontName='Courier',         fontSize=8,  textColor=DARK)

    # ── Header ────────────────────────────────────────────────────────────
    story.append(Paragraph('Finance Dashboard', h1))
    story.append(Paragraph(f'Monthly Report — {month_label}', sub))
    story.append(Paragraph(f'Generated for {user.username} on {date.today().strftime("%d %B %Y")}', sub))
    story.append(HRFlowable(width='100%', thickness=1, color=BORDER, spaceAfter=12))

    # ── Summary cards (3-column table) ────────────────────────────────────
    story.append(Paragraph('Summary', h2))

    bal_color = GREEN if balance >= 0 else RED
    summary_data = [
        ['Income', 'Expenses', 'Balance'],
        [_fmt(income), _fmt(expenses), _fmt(balance)],
    ]
    summary_table = Table(summary_data, colWidths=[56*mm, 56*mm, 56*mm])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND',  (0,0), (-1,0), LIGHT),
        ('TEXTCOLOR',   (0,0), (-1,0), MID),
        ('FONTNAME',    (0,0), (-1,0), 'Helvetica'),
        ('FONTSIZE',    (0,0), (-1,0), 8),
        ('TEXTCOLOR',   (0,1), (0,1),  GREEN),
        ('TEXTCOLOR',   (1,1), (1,1),  RED),
        ('TEXTCOLOR',   (2,1), (2,1),  bal_color),
        ('FONTNAME',    (0,1), (-1,1), 'Helvetica-Bold'),
        ('FONTSIZE',    (0,1), (-1,1), 18),
        ('ALIGN',       (0,0), (-1,-1),'CENTER'),
        ('VALIGN',      (0,0), (-1,-1),'MIDDLE'),
        ('ROWBACKGROUNDS', (0,0), (-1,-1), [LIGHT, WHITE]),
        ('BOX',         (0,0), (-1,-1), 0.5, BORDER),
        ('INNERGRID',   (0,0), (-1,-1), 0.5, BORDER),
        ('TOPPADDING',  (0,0), (-1,-1), 8),
        ('BOTTOMPADDING',(0,0),(-1,-1), 8),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 8))

    # ── Budget vs actual ──────────────────────────────────────────────────
    if budgets:
        story.append(Paragraph('Budget vs Actual', h2))
        bud_data = [['Category', 'Budget', 'Spent', 'Remaining', 'Status']]
        for b in budgets:
            spent = next(
                (c['total'] for c in by_category if c['category__name'] == b.category.name), 0
            )
            remaining = b.limit - spent
            status    = 'Over budget' if spent > b.limit else 'On track'
            bud_data.append([
                b.category.name,
                _fmt(b.limit),
                _fmt(spent),
                _fmt(remaining),
                status,
            ])

        bud_table = Table(bud_data, colWidths=[50*mm, 30*mm, 30*mm, 30*mm, 28*mm])
        bud_style = TableStyle([
            ('BACKGROUND',   (0,0), (-1,0), DARK),
            ('TEXTCOLOR',    (0,0), (-1,0), WHITE),
            ('FONTNAME',     (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE',     (0,0), (-1,-1),8),
            ('FONTNAME',     (0,1), (-1,-1),'Helvetica'),
            ('ROWBACKGROUNDS',(0,1),(-1,-1), [WHITE, LIGHT]),
            ('BOX',          (0,0), (-1,-1), 0.5, BORDER),
            ('INNERGRID',    (0,0), (-1,-1), 0.5, BORDER),
            ('TOPPADDING',   (0,0), (-1,-1), 5),
            ('BOTTOMPADDING',(0,0), (-1,-1), 5),
            ('LEFTPADDING',  (0,0), (-1,-1), 6),
        ])
        # Colour over-budget rows red
        for i, b in enumerate(budgets, start=1):
            spent = next(
                (c['total'] for c in by_category if c['category__name'] == b.category.name), 0
            )
            if spent > b.limit:
                bud_style.add('TEXTCOLOR', (4, i), (4, i), RED)
                bud_style.add('FONTNAME',  (4, i), (4, i), 'Helvetica-Bold')

        bud_table.setStyle(bud_style)
        story.append(bud_table)
        story.append(Spacer(1, 8))

    # ── Spending by category ──────────────────────────────────────────────
    if by_category:
        story.append(Paragraph('Spending by Category', h2))
        cat_data = [['Category', 'Amount', '% of Total']]
        for c in by_category:
            pct = (float(c['total']) / float(expenses) * 100) if expenses > 0 else 0
            cat_data.append([
                c['category__name'] or 'Uncategorised',
                _fmt(c['total']),
                f"{pct:.1f}%",
            ])
        # Total row
        cat_data.append(['Total', _fmt(expenses), '100%'])

        cat_table = Table(cat_data, colWidths=[90*mm, 40*mm, 38*mm])
        cat_table.setStyle(TableStyle([
            ('BACKGROUND',   (0,0),  (-1,0),  DARK),
            ('TEXTCOLOR',    (0,0),  (-1,0),  WHITE),
            ('FONTNAME',     (0,0),  (-1,0),  'Helvetica-Bold'),
            ('FONTNAME',     (0,1),  (-1,-2), 'Helvetica'),
            ('FONTNAME',     (0,-1), (-1,-1), 'Helvetica-Bold'),
            ('BACKGROUND',   (0,-1), (-1,-1), LIGHT),
            ('FONTSIZE',     (0,0),  (-1,-1), 8),
            ('ROWBACKGROUNDS',(0,1), (-1,-2), [WHITE, LIGHT]),
            ('BOX',          (0,0),  (-1,-1), 0.5, BORDER),
            ('INNERGRID',    (0,0),  (-1,-1), 0.5, BORDER),
            ('TOPPADDING',   (0,0),  (-1,-1), 5),
            ('BOTTOMPADDING',(0,0),  (-1,-1), 5),
            ('LEFTPADDING',  (0,0),  (-1,-1), 6),
            ('ALIGN',        (1,0),  (-1,-1), 'RIGHT'),
        ]))
        story.append(cat_table)
        story.append(Spacer(1, 8))

    # ── Transactions table ────────────────────────────────────────────────
    if recent_tx:
        story.append(Paragraph(f'Transactions ({len(recent_tx)} shown)', h2))
        tx_data = [['Date', 'Type', 'Amount', 'Category', 'Note']]
        for tx in recent_tx:
            tx_data.append([
                tx.date.strftime('%d %b'),
                tx.type.capitalize(),
                _fmt(tx.amount),
                tx.category.name if tx.category else '—',
                (tx.note[:35] + '…') if len(tx.note) > 35 else tx.note or '—',
            ])

        tx_table = Table(tx_data, colWidths=[18*mm, 18*mm, 28*mm, 38*mm, 66*mm])
        tx_table.setStyle(TableStyle([
            ('BACKGROUND',   (0,0),  (-1,0),  DARK),
            ('TEXTCOLOR',    (0,0),  (-1,0),  WHITE),
            ('FONTNAME',     (0,0),  (-1,0),  'Helvetica-Bold'),
            ('FONTNAME',     (0,1),  (-1,-1), 'Helvetica'),
            ('FONTSIZE',     (0,0),  (-1,-1), 7.5),
            ('ROWBACKGROUNDS',(0,1), (-1,-1), [WHITE, LIGHT]),
            ('BOX',          (0,0),  (-1,-1), 0.5, BORDER),
            ('INNERGRID',    (0,0),  (-1,-1), 0.5, BORDER),
            ('TOPPADDING',   (0,0),  (-1,-1), 4),
            ('BOTTOMPADDING',(0,0),  (-1,-1), 4),
            ('LEFTPADDING',  (0,0),  (-1,-1), 5),
        ]))

        # Colour income rows green, expense rows default
        for i, tx in enumerate(recent_tx, start=1):
            if tx.type == 'income':
                tx_table._argH  # force layout
                tx_table.setStyle(TableStyle([
                    ('TEXTCOLOR', (2, i), (2, i), GREEN),
                ]))

        story.append(tx_table)

    # ── Footer ────────────────────────────────────────────────────────────
    story.append(Spacer(1, 12))
    story.append(HRFlowable(width='100%', thickness=0.5, color=BORDER))
    story.append(Paragraph(
        f'Finance Dashboard — {month_label} report — {user.username}',
        style('Footer', fontName='Helvetica', fontSize=7, textColor=MID,
              alignment=TA_CENTER, spaceBefore=4)
    ))

    doc.build(story)
    return buf.getvalue()