"""
Vector search — embeds a query and finds the most relevant wiki chunks.

Uses the same OpenAI embedding model that was used to embed the wiki,
then calls pgvector's cosine similarity search via the search_wiki() function.
"""

import logging
from dataclasses import dataclass

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

OPENAI_API_URL = "https://api.openai.com/v1/embeddings"
EMBEDDING_DIMENSION = 1536


@dataclass
class SearchResult:
    chunk_id: int
    title: str
    section_header: str
    content: str
    page_type: str
    categories: list[str]
    similarity: float
    url: str = ""

    def __post_init__(self):
        if not self.url:
            safe_title = self.title.replace(" ", "_")
            self.url = f"https://oldschool.runescape.wiki/w/{safe_title}"


class VectorSearch:
    """Handles query embedding and pgvector similarity search."""

    def __init__(self, db_pool):
        self.pool = db_pool
        self.http_client = httpx.AsyncClient(
            timeout=30.0,
            headers={
                "Authorization": f"Bearer {settings.embedding_api_key}",
                "Content-Type": "application/json",
            },
        )

    async def close(self):
        await self.http_client.aclose()

    async def embed_query(self, text: str) -> list[float]:
        """Generate embedding for a search query."""
        response = await self.http_client.post(
            OPENAI_API_URL,
            json={
                "input": text[:8000],
                "model": settings.embedding_model,
                "dimensions": EMBEDDING_DIMENSION,
            },
        )
        response.raise_for_status()
        data = response.json()
        return data["data"][0]["embedding"]

    async def search(
        self,
        query: str,
        top_k: int = 5,
        page_type: str | None = None,
        game_mode: str | None = None,
    ) -> list[SearchResult]:
        """
        Embed a query and search for the most relevant wiki chunks.

        Args:
            query: The user's question
            top_k: Number of results to return
            page_type: Optional filter (quest, item, monster, etc.)
            game_mode: Optional filter (main, ironman, etc.)
        """
        # Step 1: Embed the query
        try:
            embedding = await self.embed_query(query)
        except Exception as e:
            logger.error(f"Failed to embed query: {e}")
            return []

        # Step 2: Search pgvector using the search_wiki() SQL function
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(
                    "SELECT * FROM search_wiki($1, $2, $3, $4)",
                    embedding,
                    top_k,
                    page_type,
                    game_mode,
                )

                return [
                    SearchResult(
                        chunk_id=row["chunk_id"],
                        title=row["page_title"],
                        section_header=row["section_header"],
                        content=row["content"],
                        page_type=row["page_type"],
                        categories=row["categories"] or [],
                        similarity=row["similarity"],
                    )
                    for row in rows
                ]

        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []
