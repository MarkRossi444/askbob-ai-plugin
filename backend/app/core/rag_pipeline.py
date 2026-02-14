"""
RAG (Retrieval-Augmented Generation) pipeline.

Orchestrates the full flow: question → embed → search → prompt → Claude → answer.
This is the core brain of WiseOldMan.Ai.
"""

import json
import logging
from collections.abc import AsyncGenerator

from app.core.vector_search import VectorSearch, SearchResult
from app.core.llm_client import LlmClient
from app.models.chat import ChatResponse, Source

logger = logging.getLogger(__name__)

# System note injected when the knowledge base has no embeddings yet
_KB_BUILDING_NOTE = (
    "IMPORTANT: The OSRS wiki knowledge base is still being built and has no "
    "searchable content yet. Answer from your general knowledge of Old School "
    "RuneScape, but tell the user that the knowledge base is still loading and "
    "your answer may not reflect the latest wiki data."
)


class RagPipeline:
    """Orchestrates retrieval and generation for OSRS questions."""

    def __init__(self, db_pool):
        self.pool = db_pool
        self.vector_search = VectorSearch(db_pool)
        self.llm = LlmClient()

    async def close(self):
        await self.vector_search.close()

    async def _has_embeddings(self) -> bool:
        """Quick check whether any embeddings exist in the DB."""
        try:
            async with self.pool.acquire() as conn:
                count = await conn.fetchval(
                    "SELECT COUNT(*) FROM wiki_embeddings LIMIT 1"
                )
                return count > 0
        except Exception:
            return False

    async def answer(
        self,
        question: str,
        game_mode: str = "main",
        conversation_history: list[dict] | None = None,
        player_context: dict | None = None,
    ) -> ChatResponse:
        """
        Full RAG pipeline: search wiki → build context → ask Claude.

        Returns:
            ChatResponse with answer, sources, and metadata
        """
        use_deep = self.llm.should_use_deep_model(question)
        top_k = 8 if use_deep else 5

        # Search for relevant wiki chunks (graceful degradation)
        results: list[SearchResult] = []
        kb_available = await self._has_embeddings()

        if kb_available:
            try:
                results = await self.vector_search.search(
                    query=question,
                    top_k=top_k,
                    game_mode=game_mode if game_mode != "main" else None,
                )
            except Exception as e:
                logger.warning(f"Vector search failed, proceeding without context: {e}")

        if results:
            logger.info(
                f"Query: '{question[:80]}' → {len(results)} chunks "
                f"(top similarity: {results[0].similarity:.3f})"
            )
        else:
            logger.info(f"Query: '{question[:80]}' → 0 chunks")

        # Build context for the LLM
        context_chunks = [
            {
                "title": r.title,
                "section_header": r.section_header,
                "content": r.content,
            }
            for r in results
        ]

        # If no embeddings exist, inject a system note so Claude responds appropriately
        if not kb_available:
            context_chunks = [{"title": "System", "section_header": "", "content": _KB_BUILDING_NOTE}]

        # Generate response with Claude
        try:
            answer_text, model_used = await self.llm.generate_response(
                question=question,
                context_chunks=context_chunks,
                game_mode=game_mode,
                use_deep_model=use_deep,
                conversation_history=conversation_history,
                player_context=player_context,
            )
        except Exception as e:
            logger.error(f"LLM generation failed: {e}", exc_info=True)
            raise RuntimeError(f"Failed to generate response: {e}") from e

        sources = self._build_sources(results)

        return ChatResponse(
            answer=answer_text,
            sources=sources,
            game_mode=game_mode,
            model=model_used,
        )

    async def answer_stream(
        self,
        question: str,
        game_mode: str = "main",
        conversation_history: list[dict] | None = None,
        player_context: dict | None = None,
    ) -> AsyncGenerator[str, None]:
        """
        Streaming RAG pipeline. Yields Server-Sent Events (SSE).

        Event format:
            data: {"type": "sources", "sources": [...]}
            data: {"type": "chunk", "text": "..."}
            data: {"type": "done", "model": "..."}
        """
        use_deep = self.llm.should_use_deep_model(question)
        top_k = 8 if use_deep else 5

        # Search for relevant wiki chunks (graceful degradation)
        results: list[SearchResult] = []
        kb_available = await self._has_embeddings()

        if kb_available:
            try:
                results = await self.vector_search.search(
                    query=question,
                    top_k=top_k,
                    game_mode=game_mode if game_mode != "main" else None,
                )
            except Exception as e:
                logger.warning(f"Vector search failed during stream, proceeding without context: {e}")

        # Send sources first
        sources = self._build_sources(results)
        sources_data = [s.model_dump() for s in sources]
        yield f"data: {json.dumps({'type': 'sources', 'sources': sources_data})}\n\n"

        # Build context for the LLM
        context_chunks = [
            {
                "title": r.title,
                "section_header": r.section_header,
                "content": r.content,
            }
            for r in results
        ]

        if not kb_available:
            context_chunks = [{"title": "System", "section_header": "", "content": _KB_BUILDING_NOTE}]

        # Stream response from Claude
        model_used = ""
        try:
            async for text_chunk, model in self.llm.generate_response_stream(
                question=question,
                context_chunks=context_chunks,
                game_mode=game_mode,
                use_deep_model=use_deep,
                conversation_history=conversation_history,
                player_context=player_context,
            ):
                model_used = model
                yield f"data: {json.dumps({'type': 'chunk', 'text': text_chunk})}\n\n"
        except Exception as e:
            logger.error(f"LLM stream failed: {e}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'message': 'Response generation failed. Please try again.'})}\n\n"

        yield f"data: {json.dumps({'type': 'done', 'model': model_used, 'game_mode': game_mode})}\n\n"

    def _build_sources(self, results: list[SearchResult]) -> list[Source]:
        """Convert search results into source citations."""
        seen_titles = set()
        sources = []

        for r in results:
            if r.title in seen_titles:
                continue
            seen_titles.add(r.title)

            sources.append(
                Source(
                    title=r.title,
                    section=r.section_header,
                    url=r.url,
                    similarity=round(r.similarity, 3),
                )
            )

        return sources[:5]
