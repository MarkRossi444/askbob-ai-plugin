"""
Vector search — embeds a query and finds the most relevant wiki chunks.

Uses the same OpenAI embedding model that was used to embed the wiki,
then calls pgvector's cosine similarity search via the search_wiki() function.

Search strategy (4 passes):
  1. Vector similarity (semantic)
  2. Title-match (keyword) — boosts chunks from pages named in the query
  3. Cross-reference (2-hop) — follows page references found in initial results
  4. Merge with boosting: title + section relevance + cross-ref
"""

import logging
from dataclasses import dataclass

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

OPENAI_API_URL = "https://api.openai.com/v1/embeddings"
EMBEDDING_DIMENSION = 1536

# Boost constants
TITLE_BOOST = 0.30      # Chunks from pages whose title appears in the query
SECTION_BOOST = 0.10     # Extra boost when section header matches query intent
XREF_BOOST = 0.20        # Chunks from cross-referenced pages (2-hop)

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
    "quest": ["details", "requirements", "rewards", "walkthrough"],
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
        # Lazy-loaded title index for cross-reference search
        self._title_index: list[tuple[str, str]] | None = None

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

    async def _get_title_index(self, conn) -> list[tuple[str, str]]:
        """Lazy-load wiki page titles for cross-reference lookups.

        Returns list of (title_lower, title_original) sorted by length
        descending so longer titles match first.
        """
        if self._title_index is None:
            rows = await conn.fetch(
                "SELECT title FROM wiki_pages WHERE LENGTH(title) >= 6"
            )
            titles = [(r["title"].lower(), r["title"]) for r in rows]
            titles.sort(key=lambda t: len(t[0]), reverse=True)
            self._title_index = titles
            logger.info(f"Loaded title index: {len(titles)} titles for cross-ref search")
        return self._title_index

    def _find_references(
        self,
        content: str,
        query: str,
        exclude_titles: set[str],
    ) -> list[str]:
        """Find wiki page titles mentioned in chunk content.

        Scans the content for page title mentions that aren't already
        in the query or the exclude set. Used for 2-hop retrieval:
        if the Barrows gloves page mentions "Recipe for Disaster",
        we'll fetch RFD chunks too.
        """
        content_lower = content.lower()
        query_lower = query.lower()

        found: list[str] = []
        found_lower: set[str] = set()

        for title_lower, title_original in self._title_index or []:
            if title_lower in exclude_titles or title_lower in found_lower:
                continue
            if title_lower in query_lower:
                continue
            if title_lower in content_lower:
                found.append(title_original)
                found_lower.add(title_lower)
                if len(found) >= 3:
                    break

        return found

    async def search(
        self,
        query: str,
        top_k: int = 5,
        page_type: str | None = None,
        game_mode: str | None = None,
    ) -> list[SearchResult]:
        """
        Hybrid search with cross-reference following.

        Pass 1: Vector similarity search (semantic)
        Pass 2: Title-match search (keyword + section boost)
        Pass 3: Cross-reference search (2-hop — follows page mentions in results)
        Then merges all results with boosting.
        """
        # Step 1: Embed the query
        try:
            embedding = await self.embed_query(query)
        except Exception as e:
            logger.error(f"Failed to embed query: {e}")
            return []

        try:
            async with self.pool.acquire() as conn:
                # ── Pass 1: Vector similarity search ──
                vector_rows = await conn.fetch(
                    "SELECT * FROM search_wiki($1, $2, $3, $4)",
                    embedding,
                    top_k,
                    page_type,
                    game_mode,
                )

                # ── Pass 2: Title-match search ──
                # Retrieve extra chunks (top_k*3) for broader section coverage.
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

                # Filter substring title collisions (e.g. "Dragon Slayer I" inside "Dragon Slayer II")
                matched_titles: set[str] = set()
                for row in title_rows:
                    matched_titles.add(row["page_title"].lower())

                shadowed: set[str] = set()
                for t in matched_titles:
                    for other in matched_titles:
                        if t != other and t in other and len(t) < len(other):
                            shadowed.add(t)

                # Section relevance keywords from the query
                section_keywords = _extract_section_keywords(query)

                # ── Merge Pass 1 + Pass 2 ──
                seen_ids: dict[int, SearchResult] = {}

                for row in title_rows:
                    cid = row["chunk_id"]
                    title_lower = row["page_title"].lower()

                    if title_lower in shadowed:
                        continue

                    boost = TITLE_BOOST
                    section = (row["section_header"] or "").lower()
                    if section and section_keywords:
                        if any(kw in section for kw in section_keywords):
                            boost += SECTION_BOOST

                    seen_ids[cid] = SearchResult(
                        chunk_id=cid,
                        title=row["page_title"],
                        section_header=row["section_header"],
                        content=row["content"],
                        page_type=row["page_type"],
                        categories=row["categories"] or [],
                        similarity=min(row["similarity"] + boost, 1.0),
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

                # ── Pass 3: Cross-reference search (2-hop) ──
                # Look at the top results so far and find wiki pages
                # mentioned in their content. Then fetch chunks from
                # those referenced pages.
                interim = sorted(seen_ids.values(), key=lambda r: r.similarity, reverse=True)
                top_content = " ".join(r.content for r in interim[:3])

                if top_content:
                    title_index = await self._get_title_index(conn)
                    exclude = matched_titles | shadowed
                    referenced = self._find_references(top_content, query, exclude)

                    if referenced:
                        logger.info(
                            f"Cross-ref: found {referenced} in top results"
                        )

                    for ref_title in referenced:
                        xref_rows = await conn.fetch(
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
                            WHERE
                                LOWER(wc.title) = LOWER($2)
                                AND ($3::text IS NULL OR wc.page_type = $3)
                                AND ($4::text IS NULL OR $4 = ANY(wc.game_modes))
                            ORDER BY we.embedding <=> $1
                            LIMIT $5
                            """,
                            embedding,
                            ref_title,
                            page_type,
                            game_mode,
                            top_k,
                        )

                        for row in xref_rows:
                            cid = row["chunk_id"]
                            if cid not in seen_ids:
                                boost = XREF_BOOST
                                section = (row["section_header"] or "").lower()
                                if section and section_keywords:
                                    if any(kw in section for kw in section_keywords):
                                        boost += SECTION_BOOST
                                seen_ids[cid] = SearchResult(
                                    chunk_id=cid,
                                    title=row["page_title"],
                                    section_header=row["section_header"],
                                    content=row["content"],
                                    page_type=row["page_type"],
                                    categories=row["categories"] or [],
                                    similarity=min(row["similarity"] + boost, 1.0),
                                )

                # Final sort and return
                results = sorted(seen_ids.values(), key=lambda r: r.similarity, reverse=True)

                if results:
                    titles_in_results = {r.title for r in results[:top_k]}
                    logger.info(
                        f"Search: '{query[:60]}' → {len(seen_ids)} candidates, "
                        f"returning {min(top_k, len(results))} from pages: {titles_in_results}"
                    )

                return results[:top_k]

        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []
