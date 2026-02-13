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
        Hybrid search: combines vector similarity with title matching.

        When a user asks about a specific page by name (e.g. "Dragon Slayer II"),
        pure vector search can miss it because generic "Requirements" sections
        from other pages score higher. This does two passes:
          1. Vector similarity search (semantic)
          2. Title-match search (keyword)
        Then merges results, boosting title-matched chunks.
        """
        # Step 1: Embed the query
        try:
            embedding = await self.embed_query(query)
        except Exception as e:
            logger.error(f"Failed to embed query: {e}")
            return []

        try:
            async with self.pool.acquire() as conn:
                # Pass 1: Vector similarity search
                vector_rows = await conn.fetch(
                    "SELECT * FROM search_wiki($1, $2, $3, $4)",
                    embedding,
                    top_k,
                    page_type,
                    game_mode,
                )

                # Pass 2: Title-match search — find chunks from pages whose
                # title appears in the query (case-insensitive)
                title_rows = await conn.fetch(
                    """
                    SELECT
                        wc.id AS chunk_id,
                        wc.title AS page_title,
                        wc.section_header,
                        wc.content,
                        wc.page_type,
                        wc.categories,
                        1 - (we.embedding <=> $1) AS similarity
                    FROM wiki_chunks wc
                    JOIN wiki_embeddings we ON we.chunk_id = wc.id
                    JOIN wiki_pages wp ON wp.page_id = wc.page_id
                    WHERE
                        LOWER($2) LIKE '%' || LOWER(wp.title) || '%'
                        AND LENGTH(wp.title) >= 4
                        AND ($3::text IS NULL OR wc.page_type = $3)
                        AND ($4::text IS NULL OR $4 = ANY(wc.game_modes))
                    ORDER BY we.embedding <=> $1
                    LIMIT $5
                    """,
                    embedding,
                    query,
                    page_type,
                    game_mode,
                    top_k,
                )

                # Merge: title-matched chunks get a similarity boost
                TITLE_BOOST = 0.15
                seen_ids: dict[int, SearchResult] = {}

                for row in title_rows:
                    cid = row["chunk_id"]
                    boosted_sim = min(row["similarity"] + TITLE_BOOST, 1.0)
                    seen_ids[cid] = SearchResult(
                        chunk_id=cid,
                        title=row["page_title"],
                        section_header=row["section_header"],
                        content=row["content"],
                        page_type=row["page_type"],
                        categories=row["categories"] or [],
                        similarity=boosted_sim,
                    )

                for row in vector_rows:
                    cid = row["chunk_id"]
                    if cid not in seen_ids:
                        seen_ids[cid] = SearchResult(
                            chunk_id=cid,
                            title=row["page_title"],
                            section_header=row["section_header"],
                            content=row["content"],
                            page_type=row["page_type"],
                            categories=row["categories"] or [],
                            similarity=row["similarity"],
                        )

                # Sort by similarity descending, return top_k
                results = sorted(seen_ids.values(), key=lambda r: r.similarity, reverse=True)
                return results[:top_k]

        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []
