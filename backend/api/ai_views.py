"""
AI endpoints:

POST /api/ai/chat/          → streaming SSE response
GET  /api/ai/providers/     → list providers + which is active
POST /api/ai/providers/     → switch active provider + save keys
GET  /api/ai/context/       → debug: show what data the AI can see
"""

from django.http import StreamingHttpResponse
from django.conf import settings
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def ai_chat(request):
    """
    POST /api/ai/chat/
    Body: {
        "messages": [{"role":"user","content":"..."}, ...],
        "month":    "2026-04",       // optional
        "provider": "gemini"         // optional override
    }
    Returns Server-Sent Events stream.
    """
    messages = request.data.get('messages', [])
    month    = request.data.get('month', None)
    provider = request.data.get('provider', None)

    if not messages:
        return Response({'error': 'messages field is required'}, status=400)

    for msg in messages:
        if msg.get('role') not in ('user', 'assistant'):
            return Response({'error': 'role must be "user" or "assistant"'}, status=400)

    def event_stream():
        try:
            from api.ai_service import stream_ai_response
            for chunk in stream_ai_response(request.user, messages, month=month, provider=provider):
                safe = chunk.replace('\n', '\\n')
                yield f"data: {safe}\n\n"
        except Exception as e:
            yield f"data: Error: {str(e)}\n\n"
        finally:
            yield "data: [DONE]\n\n"

    response = StreamingHttpResponse(event_stream(), content_type='text/event-stream')
    response['Cache-Control']     = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def ai_providers(request):
    """
    GET  /api/ai/providers/ → returns provider status + active provider
    POST /api/ai/providers/ → update active provider and/or API keys
        Body: {
            "provider":     "gemini",           // new active provider
            "anthropic_key": "sk-ant-...",       // optional
            "gemini_key":    "AIza...",          // optional
            "ollama_model":  "llama3",           // optional
            "ollama_url":    "http://localhost:11434"  // optional
        }
    """
    if request.method == 'GET':
        from api.ai_service import get_provider_status
        return Response(get_provider_status())

    # POST — update settings at runtime
    data = request.data

    if 'provider' in data:
        p = data['provider'].lower()
        if p not in ('claude', 'gemini', 'ollama'):
            return Response({'error': 'provider must be claude, gemini, or ollama'}, status=400)
        settings.AI_PROVIDER = p

    if 'anthropic_key' in data and data['anthropic_key']:
        settings.ANTHROPIC_API_KEY = data['anthropic_key']

    if 'gemini_key' in data and data['gemini_key']:
        settings.GEMINI_API_KEY = data['gemini_key']

    if 'ollama_model' in data and data['ollama_model']:
        settings.OLLAMA_MODEL = data['ollama_model']

    if 'ollama_url' in data and data['ollama_url']:
        settings.OLLAMA_BASE_URL = data['ollama_url']

    from api.ai_service import get_provider_status
    return Response({'success': True, **get_provider_status()})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def ai_context(request):
    """
    GET /api/ai/context/?month=2026-04
    Debug endpoint — shows the exact data block sent to the AI.
    """
    month = request.query_params.get('month', None)
    try:
        from api.ai_service import build_financial_context
        return Response({'context': build_financial_context(request.user, month=month)})
    except Exception as e:
        return Response({'error': str(e)}, status=503)