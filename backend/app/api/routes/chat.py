"""Chat API routes — the main endpoints players interact with."""

import asyncio
import json
import logging
import time

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from app.models.chat import ChatRequest, ChatResponse

logger = logging.getLogger(__name__)

router = APIRouter()

VALID_GAME_MODES = {"main", "ironman", "hardcore_ironman", "ultimate_ironman", "group_ironman"}


def _get_request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "--------")


@router.post("/chat", response_model=ChatResponse)
async def chat(chat_request: ChatRequest, request: Request):
    """
    Ask the Wise Old Man a question about OSRS.

    Returns a complete response with sources. For streaming responses,
    use POST /api/chat/stream instead.
    """
    from app.main import get_rag_pipeline, response_times

    req_id = _get_request_id(request)
    _validate_game_mode(chat_request.game_mode)

    start = time.time()

    try:
        pipeline = get_rag_pipeline()
        # Convert Message models to dicts for the LLM client
        conversation_history = [
            {"role": m.role, "content": m.content} for m in chat_request.messages
        ] if chat_request.messages else None
        response = await asyncio.wait_for(
            pipeline.answer(
                question=chat_request.question,
                game_mode=chat_request.game_mode,
                conversation_history=conversation_history,
            ),
            timeout=45.0,
        )
    except asyncio.TimeoutError:
        logger.warning(f"[{req_id}] Chat request timed out after 45s")
        raise HTTPException(status_code=504, detail="Response timed out. Please try a simpler question.")
    except Exception as e:
        logger.error(f"[{req_id}] Chat error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to generate response")

    elapsed_ms = (time.time() - start) * 1000
    response_times.append(elapsed_ms)
    logger.info(
        f"[{req_id}] Chat response in {elapsed_ms / 1000:.2f}s | "
        f"mode={chat_request.game_mode} | "
        f"sources={len(response.sources)} | "
        f"model={response.model}"
    )

    try:
        from app.main import get_stats_tracker
        stats = get_stats_tracker()
        stats.record_game_mode(chat_request.game_mode)
        stats.record_model(response.model)
        stats.record_latency("total", elapsed_ms)
    except RuntimeError:
        pass

    return response


@router.post("/chat/stream")
async def chat_stream(chat_request: ChatRequest, request: Request):
    """
    Ask the Wise Old Man a question — streaming response.

    Returns a Server-Sent Events stream with:
    - sources event (wiki pages used)
    - chunk events (answer text arriving word-by-word)
    - done event (metadata)
    """
    from app.main import get_rag_pipeline, response_times

    req_id = _get_request_id(request)
    _validate_game_mode(chat_request.game_mode)

    pipeline = get_rag_pipeline()

    # Convert Message models to dicts for the LLM client
    conversation_history = [
        {"role": m.role, "content": m.content} for m in chat_request.messages
    ] if chat_request.messages else None

    start = time.time()

    async def _safe_stream(generator):
        model_used = ""
        try:
            async for chunk in generator:
                # Extract model from the done event
                if '"type": "done"' in chunk:
                    try:
                        data = json.loads(chunk.split("data: ", 1)[1])
                        model_used = data.get("model", "")
                    except (IndexError, json.JSONDecodeError):
                        pass
                yield chunk
        except Exception as e:
            logger.error(f"[{req_id}] Stream error: {e}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'message': 'Response interrupted. Please try again.'})}\n\n"
        finally:
            elapsed_ms = (time.time() - start) * 1000
            response_times.append(elapsed_ms)
            logger.info(f"[{req_id}] Stream completed in {elapsed_ms:.0f}ms")
            try:
                from app.main import get_stats_tracker
                stats = get_stats_tracker()
                stats.record_game_mode(chat_request.game_mode)
                if model_used:
                    stats.record_model(model_used)
                stats.record_latency("total", elapsed_ms)
            except RuntimeError:
                pass

    return StreamingResponse(
        _safe_stream(pipeline.answer_stream(
            question=chat_request.question,
            game_mode=chat_request.game_mode,
            conversation_history=conversation_history,
        )),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def _validate_game_mode(game_mode: str):
    if game_mode not in VALID_GAME_MODES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid game mode '{game_mode}'. "
                   f"Valid modes: {', '.join(sorted(VALID_GAME_MODES))}",
        )
