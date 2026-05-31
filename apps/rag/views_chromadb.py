"""
RAG API Views for querying the knowledge base with Agno Agent-based routing.
"""
import json
import os
import time
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django.conf import settings
from django.http import StreamingHttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt

from .rag_service_chromadb import RAGServiceChroma
from .agents.orchestrator_agno import OrchestratorAgent


# Initialize Agno agent system (singleton pattern)
_orchestrator = None

def get_orchestrator():
    """Get or create the Agno orchestrator agent."""
    global _orchestrator
    if _orchestrator is None:
        # Get OpenAI API key from settings
        api_key = getattr(settings, 'OPENAI_API_KEY', os.getenv('OPENAI_API_KEY'))
        
        # Create orchestrator with Agno agents
        _orchestrator = OrchestratorAgent(api_key=api_key)
    
    return _orchestrator


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def rag_query(request):
    """
    RAG Query Endpoint - Agent-based routing to handle different query types
    
    Request body:
    {
        "query": "What are the features of Honda BR-V?",  // General query
        // OR
        "query": "What changes did Suzuki make last week?",  // HTML diff query
        "top_k": 5,  // optional, default 5
        "competitor_filter": "honda"  // optional: honda, suzuki, kia, or all
    }
    
    The orchestrator will automatically detect the query type and route to:
    - GeneralQueryAgent: For product/feature/price queries
    - HTMLDiffAgent: For website change/difference queries
    """
    query_text = request.data.get('query')
    
    if not query_text:
        return Response(
            {'error': 'Query text is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    top_k = request.data.get('top_k', 5)
    competitor_filter = request.data.get('competitor_filter', 'all')
    
    if not isinstance(top_k, int) or top_k < 1 or top_k > 20:
        return Response(
            {'error': 'top_k must be an integer between 1 and 20'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        orchestrator = get_orchestrator()
        context = {
            'user': request.user,
            'user_id': request.user.id,
            'top_k': top_k,
            'competitor_filter': competitor_filter,
        }
        result = orchestrator.execute(query_text, context)
        
        return Response(result, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': f'Error processing query: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def semantic_search(request):
    """
    Semantic Search Endpoint - Hybrid retrieval only, no answer generation
    
    Request body:
    {
        "query": "Honda BR-V price",
        "top_k": 10,  // optional, default 5
        "competitor_filter": "honda"  // optional
    }
    """
    query_text = request.data.get('query')
    
    if not query_text:
        return Response(
            {'error': 'Query text is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    top_k = request.data.get('top_k', 10)
    competitor_filter = request.data.get('competitor_filter', 'all')
    
    try:
        rag_service = RAGServiceChroma()
        result = rag_service.semantic_search(
            query=query_text,
            top_k=top_k,
            competitor_filter=competitor_filter,
            user_id=request.user.id,
        )
        
        return Response(result, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {'error': f'Error performing search: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def rag_stats(request):
    """
    RAG System Statistics
    
    Returns total chunks, chunks per competitor, and system info
    """
    try:
        rag_service = RAGServiceChroma()
        stats = rag_service.get_stats(user_id=request.user.id)
        return Response(stats, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {'error': f'Error fetching statistics: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_competitors(request):
    """
    Get list of competitors for dropdown
    
    Returns list of competitors with their chunk counts
    """
    try:
        rag_service = RAGServiceChroma()
        competitors = rag_service.get_competitors(user_id=request.user.id)
        all_option = {
            'name': 'All Competitors',
            'value': 'all',
            'chunk_count': sum(c['chunk_count'] for c in competitors),
        }
        return Response({'competitors': [all_option] + competitors}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {'error': f'Error fetching competitors: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@csrf_exempt
def rag_query_stream(request):
    """
    Streaming RAG endpoint using Server-Sent Events (SSE).

    POST /api/rag/query/stream/
    Headers: Authorization: Token <token>
    Body:    {"query": "...", "top_k": 10, "competitor_filter": "all"}

    SSE events emitted:
      data: {"type": "metadata", "retrieved_chunks": [...], "retrieval_time": 0.1, "cache_hit": false}
      data: {"type": "chunk", "content": "token text"}
      data: {"type": "done", "generation_time": 2.3, "total_time": 2.5}
      data: {"type": "error", "message": "..."}
    """
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    # Manual token auth (DRF @api_view is incompatible with StreamingHttpResponse)
    auth_header = request.META.get("HTTP_AUTHORIZATION", "")
    if not auth_header.startswith("Token "):
        return JsonResponse({"error": "Authentication required"}, status=401)
    try:
        token = Token.objects.select_related("user").get(key=auth_header[6:])
    except Token.DoesNotExist:
        return JsonResponse({"error": "Invalid token"}, status=401)

    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"error": "Invalid JSON body"}, status=400)

    query_text = body.get("query", "").strip()
    if not query_text:
        return JsonResponse({"error": "Query text is required"}, status=400)

    top_k = body.get("top_k", None)
    competitor_filter = body.get("competitor_filter", "all") or "all"

    stream_user_id = token.user.id

    def event_stream():
        start = time.time()
        rag = RAGServiceChroma()
        from django.conf import settings as _settings
        top_k_val = top_k or getattr(_settings, "RAG_TOP_K", 10)

        try:
            # --- Cache check ---
            import hashlib
            from django.core.cache import cache
            rag_cache_ttl = getattr(_settings, "RAG_CACHE_TTL", 7200)
            cache_key = None
            if rag_cache_ttl > 0:
                raw_key = f"rag:{stream_user_id}:{query_text.lower()}:{competitor_filter}:{top_k_val}"
                cache_key = "rag_" + hashlib.md5(raw_key.encode()).hexdigest()
                cached = cache.get(cache_key)
                if cached is not None:
                    meta = {
                        "type": "metadata",
                        "retrieved_chunks": cached.get("retrieved_chunks", []),
                        "retrieval_time": cached.get("retrieval_time", 0),
                        "cache_hit": True,
                    }
                    yield f"data: {json.dumps(meta)}\n\n"
                    yield f"data: {json.dumps({'type': 'chunk', 'content': cached['answer']})}\n\n"
                    yield f"data: {json.dumps({'type': 'done', 'generation_time': 0, 'total_time': round(time.time() - start, 3)})}\n\n"
                    return

            # --- Retrieval ---
            search_results = rag.semantic_search(query_text, top_k_val, competitor_filter, user_id=stream_user_id)
            retrieval_time = search_results["retrieval_time"]
            chunks = search_results["results"]

            meta_event = {
                "type": "metadata",
                "retrieved_chunks": [
                    {"text": c["text"][:200] + "...", "metadata": c["metadata"], "score": c["fusion_score"]}
                    for c in chunks
                ],
                "retrieval_time": retrieval_time,
                "cache_hit": False,
            }
            yield f"data: {json.dumps(meta_event)}\n\n"

            # --- Streaming generation ---
            gen_start = time.time()
            full_answer = []
            for delta in rag.generate_answer_stream(query_text, chunks):
                full_answer.append(delta)
                yield f"data: {json.dumps({'type': 'chunk', 'content': delta})}\n\n"

            generation_time = round(time.time() - gen_start, 3)
            total_time = round(time.time() - start, 3)
            yield f"data: {json.dumps({'type': 'done', 'generation_time': generation_time, 'total_time': total_time})}\n\n"

            # --- Cache the full answer for future requests ---
            if cache_key and rag_cache_ttl > 0:
                cache.set(cache_key, {
                    "answer": "".join(full_answer),
                    "retrieved_chunks": meta_event["retrieved_chunks"],
                    "retrieval_time": retrieval_time,
                    "generation_time": generation_time,
                    "total_time": total_time,
                    "cache_hit": False,
                }, rag_cache_ttl)

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    response = StreamingHttpResponse(event_stream(), content_type="text/event-stream")
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"  # tells nginx not to buffer SSE
    return response


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def agent_stats(request):
    """
    Get Agent System Statistics
    
    Returns statistics about agent executions and routing
    """
    try:
        orchestrator = get_orchestrator()
        
        # Get stats for all agents
        agent_statistics = {
            'orchestrator': orchestrator.get_stats(),
            'agents': []
        }
        
        for agent in orchestrator.agents:
            agent_statistics['agents'].append(agent.get_stats())
        
        return Response(agent_statistics, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {'error': f'Error fetching agent statistics: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

