"""
ai_service.py — Multi-provider AI assistant for Finance Dashboard

Supports three providers:
  - claude   : Anthropic Claude (requires ANTHROPIC_API_KEY)
  - gemini   : Google Gemini   (requires GEMINI_API_KEY, free tier available)
  - ollama   : Local Ollama    (no key needed, runs on your machine)

The active provider is read from the AI_PROVIDER Django setting,
which the frontend can update via the /api/ai/settings/ endpoint.

Public API:
    build_financial_context(user, month=None) -> str
    stream_ai_response(user, messages, month=None, provider=None) -> generator
    get_provider_status() -> dict
"""

import os
from datetime import date
from decimal import Decimal
from django.conf import settings
from django.db.models import Sum, Q


# ── Helpers ───────────────────────────────────────────────────────────────────

def _fmt(amount) -> str:
    try:
        return f"£{float(amount):,.2f}"
    except (TypeError, ValueError):
        return "£0.00"


def get_active_provider() -> str:
    """Returns the currently configured provider: 'claude', 'gemini', or 'ollama'."""
    return getattr(settings, 'AI_PROVIDER', 'gemini').lower()


def get_provider_status() -> dict:
    """Returns which providers are configured and ready to use."""
    return {
        'active': get_active_provider(),
        'claude': {
            'available': bool(getattr(settings, 'ANTHROPIC_API_KEY', '')),
            'model':     getattr(settings, 'CLAUDE_MODEL', 'claude-sonnet-4-5'),
            'note':      'Requires paid API key from console.anthropic.com',
        },
        'gemini': {
            'available': bool(getattr(settings, 'GEMINI_API_KEY', '')),
            'model':     getattr(settings, 'GEMINI_MODEL', 'gemini-2.0-flash'),
            'note':      'Free tier available at aistudio.google.com',
        },
        'ollama': {
            'available': _check_ollama(),
            'model':     getattr(settings, 'OLLAMA_MODEL', 'llama3'),
            'note':      'Runs locally — install from ollama.ai',
        },
    }


def _check_ollama() -> bool:
    """Quick check if Ollama is running locally."""
    try:
        import urllib.request
        urllib.request.urlopen('http://localhost:11434/api/tags', timeout=1)
        return True
    except Exception:
        return False


# ── Financial context builder ─────────────────────────────────────────────────

def build_financial_context(user, month: str | None = None) -> str:
    """
    Queries the user's DB data and returns a plain-English context block
    that any AI provider can reason over.
    """
    from api.models import Transaction, Budget, RecurringTransaction, Category

    today = date.today()
    if not month:
        month = f"{today.year}-{str(today.month).zfill(2)}"

    try:
        year, mon = month.split('-')
        year, mon = int(year), int(mon)
    except ValueError:
        year, mon = today.year, today.month

    month_label = date(year, mon, 1).strftime('%B %Y')

    # Monthly totals
    month_qs = Transaction.objects.filter(user=user, date__year=year, date__month=mon)
    totals   = month_qs.aggregate(
        income   = Sum('amount', filter=Q(type='income')),
        expenses = Sum('amount', filter=Q(type='expense')),
    )
    income   = totals['income']   or Decimal('0')
    expenses = totals['expenses'] or Decimal('0')
    balance  = income - expenses

    # Per-category breakdown
    by_category = list(
        month_qs.filter(type='expense')
        .values('category__name')
        .annotate(total=Sum('amount'))
        .order_by('-total')
    )

    # Budget vs actual
    budgets      = Budget.objects.filter(user=user, month=month).select_related('category')
    budget_lines = []
    for b in budgets:
        spent  = next((c['total'] for c in by_category if c['category__name'] == b.category.name), 0)
        status = 'OVER BUDGET' if spent > b.limit else 'within budget'
        budget_lines.append(
            f"  - {b.category.name}: limit {_fmt(b.limit)}, spent {_fmt(spent)} ({status})"
        )

    # Recent transactions (last 10)
    recent   = month_qs.select_related('category').order_by('-date', '-created_at')[:10]
    tx_lines = []
    for tx in recent:
        cat   = tx.category.name if tx.category else 'uncategorised'
        note  = f' — "{tx.note}"' if tx.note else ''
        fx    = f' (originally {tx.original_currency} {tx.original_amount})' \
                if tx.original_currency and tx.original_currency != 'GBP' else ''
        tx_lines.append(f"  - {tx.date} | {tx.type} | {_fmt(tx.amount)} | {cat}{note}{fx}")

    # All-time count
    all_tx_count = Transaction.objects.filter(user=user).count()

    # Previous month comparison
    prev_mon = mon - 1 if mon > 1 else 12
    prev_yr  = year if mon > 1 else year - 1
    prev_totals = Transaction.objects.filter(
        user=user, date__year=prev_yr, date__month=prev_mon
    ).aggregate(expenses=Sum('amount', filter=Q(type='expense')))
    prev_exp    = prev_totals['expenses'] or Decimal('0')
    exp_change  = expenses - prev_exp
    exp_str     = (
        f"{_fmt(abs(exp_change))} {'more' if exp_change > 0 else 'less'} than last month"
        if prev_exp > 0 else "no previous month data"
    )

    # Recurring rules
    recurring = RecurringTransaction.objects.filter(user=user, active=True)
    rec_lines = [
        f"  - {r.note or r.type} | {r.frequency} | {_fmt(r.amount)} | next due {r.next_due}"
        for r in recurring
    ]

    # Categories
    cat_names = ', '.join(
        c.name for c in Category.objects.filter(user=user)
    ) or 'none set up'

    # Assemble
    lines = [
        f"USER FINANCIAL DATA — {month_label}",
        f"Username: {user.username}",
        "",
        "MONTHLY SUMMARY:",
        f"  Income:   {_fmt(income)}",
        f"  Expenses: {_fmt(expenses)}",
        f"  Balance:  {_fmt(balance)}",
        f"  vs previous month: {exp_str}",
        "",
    ]
    if by_category:
        lines.append("SPENDING BY CATEGORY:")
        for c in by_category:
            lines.append(f"  - {c['category__name'] or 'Uncategorised'}: {_fmt(c['total'])}")
        lines.append("")
    if budget_lines:
        lines.append("BUDGET STATUS:")
        lines.extend(budget_lines)
        lines.append("")
    if tx_lines:
        lines.append(f"RECENT TRANSACTIONS (last 10 of {month_label}):")
        lines.extend(tx_lines)
        lines.append("")
    if rec_lines:
        lines.append("ACTIVE RECURRING RULES:")
        lines.extend(rec_lines)
        lines.append("")
    lines += [
        f"ALL-TIME: {all_tx_count} transactions total",
        f"CATEGORIES: {cat_names}",
        f"TODAY: {today.strftime('%d %B %Y')}",
    ]
    return '\n'.join(lines)


# ── System prompt ─────────────────────────────────────────────────────────────

def _build_system_prompt(user, month) -> str:
    context = build_financial_context(user, month=month)
    return f"""You are a helpful personal finance assistant built into the user's finance dashboard.
You have access to their real financial data shown below. Use it to give specific, personalised advice.

Be conversational, concise and direct. Use £ for amounts. When you spot something interesting
(over-budget categories, unusual spending, improving trends) mention it proactively.
Never make up numbers — only reference figures from the data provided.

{context}"""


# ── Provider: Claude ──────────────────────────────────────────────────────────

def _stream_claude(messages, system_prompt):
    try:
        import anthropic
    except ImportError:
        yield "Error: anthropic package not installed. Run: pip install anthropic"
        return

    api_key = getattr(settings, 'ANTHROPIC_API_KEY', '') or os.environ.get('ANTHROPIC_API_KEY', '')
    if not api_key:
        yield "Error: ANTHROPIC_API_KEY is not configured. Add it in AI Settings."
        return

    model = getattr(settings, 'CLAUDE_MODEL', 'claude-sonnet-4-5')
    client = anthropic.Anthropic(api_key=api_key)

    try:
        with client.messages.stream(
            model=model,
            max_tokens=1024,
            system=system_prompt,
            messages=messages,
        ) as stream:
            for text in stream.text_stream:
                yield text
    except anthropic.APIError as e:
        yield f"\n\nClaude API error: {str(e)}"
    except Exception as e:
        yield f"\n\nUnexpected error: {str(e)}"


# ── Provider: Gemini ──────────────────────────────────────────────────────────

def _stream_gemini(messages, system_prompt):
    try:
        import google.generativeai as genai
        from google.api_core.exceptions import ResourceExhausted
    except ImportError:
        yield "Error: google-generativeai not installed. Run: pip install google-generativeai"
        return

    api_key = getattr(settings, 'GEMINI_API_KEY', '') or os.environ.get('GEMINI_API_KEY', '')
    if not api_key:
        yield "Error: GEMINI_API_KEY is not configured. Add it in AI Settings."
        return

    model_name = getattr(settings, 'GEMINI_MODEL', 'gemini-1.5-flash')
    genai.configure(api_key=api_key)

    model = genai.GenerativeModel(
        model_name=model_name,
        system_instruction=system_prompt,
    )

    # Convert message format: 'assistant' → 'model' for Gemini
    history = []
    for msg in messages[:-1]:
        history.append({
            'role':  'model' if msg['role'] == 'assistant' else 'user',
            'parts': [msg['content']],
        })

    chat = model.start_chat(history=history)
    last = messages[-1]['content']

    import time
    max_retries = 3
    delay = 5
    for attempt in range(max_retries):
        try:
            response = chat.send_message(last, stream=True)
            for chunk in response:
                if chunk.text:
                    yield chunk.text
            return
        except ResourceExhausted:
            if attempt < max_retries - 1:
                time.sleep(delay)
                delay *= 2
            else:
                yield (
                    "\n\nGemini rate limit reached (free-tier quota exhausted for today). "
                    "Try switching to Ollama in AI Settings, or wait until tomorrow for the quota to reset."
                )
        except Exception as e:
            yield f"\n\nGemini error: {str(e)}"
            return


# ── Provider: Ollama ──────────────────────────────────────────────────────────

def _stream_ollama(messages, system_prompt):
    import json
    import urllib.request

    base_url   = getattr(settings, 'OLLAMA_BASE_URL', 'http://localhost:11434')
    model_name = getattr(settings, 'OLLAMA_MODEL', 'llama3')

    # Prepend system prompt as a system message
    ollama_messages = [{'role': 'system', 'content': system_prompt}] + messages

    payload = json.dumps({
        'model':    model_name,
        'messages': ollama_messages,
        'stream':   True,
    }).encode('utf-8')

    try:
        req = urllib.request.Request(
            f'{base_url}/api/chat',
            data=payload,
            headers={'Content-Type': 'application/json'},
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            for line in resp:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    content = data.get('message', {}).get('content', '')
                    if content:
                        yield content
                    if data.get('done'):
                        break
                except json.JSONDecodeError:
                    continue

    except Exception as e:
        msg = str(e)
        if 'Connection refused' in msg or 'ConnectionRefused' in msg:
            yield (
                "Ollama is not running or not installed.\n\n"
                "To install: https://ollama.ai\n"
                "Then run:   ollama pull llama3\n"
                "Then run:   ollama serve"
            )
        else:
            yield f"Ollama error: {msg}"


# ── Public streaming function ─────────────────────────────────────────────────

def stream_ai_response(user, messages: list[dict], month: str | None = None, provider: str | None = None):
    """
    Stream a response from the configured AI provider.

    provider: override the default — 'claude', 'gemini', or 'ollama'
    Yields text chunks as they arrive.
    """
    active        = (provider or get_active_provider()).lower()
    system_prompt = _build_system_prompt(user, month)

    if active == 'claude':
        yield from _stream_claude(messages, system_prompt)
    elif active == 'gemini':
        yield from _stream_gemini(messages, system_prompt)
    elif active == 'ollama':
        yield from _stream_ollama(messages, system_prompt)
    else:
        yield f"Error: Unknown provider '{active}'. Choose claude, gemini, or ollama."