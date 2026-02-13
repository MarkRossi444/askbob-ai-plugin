"""
Vector search — embeds a query and finds the most relevant wiki chunks.

Uses the same OpenAI embedding model that was used to embed the wiki,
then calls pgvector's cosine similarity search via the search_wiki() function.
"""

import logging
import re
from dataclasses import dataclass

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

OPENAI_API_URL = "https://api.openai.com/v1/embeddings"
EMBEDDING_DIMENSION = 1536

# Maps query keywords → section headers that are likely relevant
_SECTION_KEYWORDS: dict[str, list[str]] = {
    "requirement": ["requirements", "details", "quest requirements", "skill requirements"],
    "drop": ["drops", "drop rates", "loot", "rare drop table"],
    "strateg": ["strategy", "strategies", "guide", "walkthrough"],
    "reward": ["rewards", "completion"],
    "location": ["location", "getting there", "how to get there"],
    "how to get": ["location", "getting there", "transportation"],
    "where": ["location", "getting there"],
    "spec": ["special attack", "combat"],
    "stats": ["stats", "bonuses", "combat stats"],
    "price": ["price", "value", "cost", "exchange"],
}


def _extract_section_keywords(query: str) -> set[str]:
    """Extract likely section header keywords from a query."""
    q = query.lower()
    keywords: set[str] = set()
    for trigger, sections in _SECTION_KEYWORDS.items():
        if trigger in q:
            keywords.update(sections)
    return keywords


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
        # Strip whitespace/newlines from key — Render env vars sometimes
        # pick up stray newlines when pasted into the dashboard
        clean_key = settings.embedding_api_key.strip().replace("\n", "").replace("\r", "").replace(" ", "")
        self.http_client = httpx.AsyncClient(
            timeout=30.0,
            headers={
                "Authorization": f"Bearer {clean_key}",
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
        from other pages score higher. This does three passes:
          1. Vector similarity search (semantic)
          2. Title-match search (keyword) — retrieves many chunks from matching pages
          3. Merge with boosting: title match + section relevance + longest-title priority
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
                # title appears in the query. Retrieve extra chunks (top_k*3)
                # so we get broader section coverage from the matched page.
                title_rows = await conn.fetch(
                    """
                    SELECT
                        wc.id AS chunk_id,
                        wc.title AS page_title,
                        wc.section_header,
                        wc.content,
                        wc.page_type,
                        wc.categories,
                        1 - (we.embedding <=> $1) AS similarity,
                        LENGTH(wp.title) AS title_length
                    FROM wiki_chunks wc
                    JOIN wiki_embeddings we ON we.chunk_id = wc.id
                    JOIN wiki_pages wp ON wp.page_id = wc.page_id
                    WHERE
                        LOWER($2) LIKE '%' || LOWER(wp.title) || '%'
                        AND LENGTH(wp.title) >= 4
                        AND ($3::text IS NULL OR wc.page_type = $3)
                        AND ($4::text IS NULL OR $4 = ANY(wc.game_modes))
                    ORDER BY LENGTH(wp.title) DESC, we.embedding <=> $1
                    LIMIT $5
                    """,
                    embedding,
                    query,
                    page_type,
                    game_mode,
                    top_k * 3,
                )

                # Collect all matched title names to filter substring collisions
                # e.g. "Dragon Slayer I" matching inside "Dragon Slayer II"
                matched_titles: set[str] = set()
                for row in title_rows:
                    matched_titles.add(row["page_title"].lower())

                # Build set of "shadowed" titles — shorter titles that are
                # substrings of a longer matched title
                shadowed: set[str] = set()
                for t in matched_titles:
                    for other in matched_titles:
                        if t != other and t in other and len(t) < len(other):
                            shadowed.add(t)

                # Section relevance keywords from the query
                section_keywords = _extract_section_keywords(query)

                # Merge: title-matched chunks get boosts
                TITLE_BOOST = 0.30
                SECTION_BOOST = 0.10
                seen_ids: dict[int, SearchResult] = {}

                for row in title_rows:
                    cid = row["chunk_id"]
                    title_lower = row["page_title"].lower()

                    # Skip chunks from shadowed (substring) title matches
                    if title_lower in shadowed:
                        continue

                    boost = TITLE_BOOST

                    # Extra boost when section header matches query intent
                    section = (row["section_header"] or "").lower()
                    if section and section_keywords:
                        if any(kw in section for kw in section_keywords):
                            boost += SECTION_BOOST

                    boosted_sim = min(row["similarity"] + boost, 1.0)
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

                if results:
                    logger.debug(
                        f"Search merge: {len(seen_ids)} unique chunks, "
                        f"top={results[0].title}>{results[0].section_header} ({results[0].similarity:.3f})"
                    )

                return results[:top_k]

        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []
