"""
Database client for storing scraped wiki data in PostgreSQL + pgvector.
"""

import json
import logging
import os
from datetime import datetime, timezone

import asyncpg
from pgvector.asyncpg import register_vector

logger = logging.getLogger(__name__)


class WikiDatabase:
    """Async PostgreSQL client for wiki data storage."""

    def __init__(self, database_url: str | None = None):
        self.database_url = database_url or os.getenv("DATABASE_URL", "")
        if not self.database_url:
            raise ValueError(
                "Database URL required. Set DATABASE_URL env var "
                "or pass database_url parameter."
            )
        self.pool: asyncpg.Pool | None = None

    async def connect(self):
        """Create connection pool with pgvector registered on every connection."""
        async def _init_conn(conn):
            await register_vector(conn)

        self.pool = await asyncpg.create_pool(
            self.database_url,
            min_size=2,
            max_size=10,
            init=_init_conn,
        )
        logger.info("Database connected")

    async def close(self):
        if self.pool:
            await self.pool.close()

    async def upsert_page(self, page) -> None:
        """Insert or update a wiki page."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO wiki_pages (page_id, title, content, categories, page_type, url, content_hash, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                ON CONFLICT (page_id) DO UPDATE SET
                    title = EXCLUDED.title,
                    content = EXCLUDED.content,
                    categories = EXCLUDED.categories,
                    page_type = EXCLUDED.page_type,
                    url = EXCLUDED.url,
                    content_hash = EXCLUDED.content_hash,
                    last_scraped = NOW(),
                    updated_at = EXCLUDED.updated_at
                """,
                page.page_id,
                page.title,
                page.content,
                page.categories,
                page.page_type,
                page.url,
                page.content_hash,
                datetime.now(timezone.utc),
            )

    async def page_needs_update(self, page_id: int, content_hash: str) -> bool:
        """Check if a page has changed by comparing content hashes."""
        async with self.pool.acquire() as conn:
            existing_hash = await conn.fetchval(
                "SELECT content_hash FROM wiki_pages WHERE page_id = $1",
                page_id,
            )
            return existing_hash != content_hash

    async def upsert_chunks(self, chunks: list) -> list[int]:
        """Insert or update chunks for a page. Returns chunk DB IDs.

        Wraps the delete + insert in a transaction for atomicity.
        """
        if not chunks:
            return []

        async with self.pool.acquire() as conn:
            async with conn.transaction():
                # Delete existing chunks for this page (re-chunking)
                page_id = chunks[0].page_id
                await conn.execute(
                    "DELETE FROM wiki_chunks WHERE page_id = $1",
                    page_id,
                )

                chunk_ids = []
                for chunk in chunks:
                    row = await conn.fetchrow(
                        """
                        INSERT INTO wiki_chunks
                            (page_id, chunk_index, title, section_header, content,
                             token_count, page_type, categories, game_modes, metadata)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                        RETURNING id
                        """,
                        chunk.page_id,
                        chunk.chunk_index,
                        chunk.title,
                        chunk.section_header,
                        chunk.content,
                        chunk.token_count,
                        chunk.page_type,
                        chunk.categories,
                        chunk.game_modes,
                        json.dumps(chunk.metadata),
                    )
                    chunk_ids.append(row["id"])

                return chunk_ids

    async def upsert_embeddings(
        self, chunk_ids: list[int], embeddings: list[list[float]], model: str
    ) -> None:
        """Store embeddings for chunks, wrapped in a transaction."""
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                for chunk_id, embedding in zip(chunk_ids, embeddings):
                    await conn.execute(
                        """
                        INSERT INTO wiki_embeddings (chunk_id, embedding, model)
                        VALUES ($1, $2, $3)
                        ON CONFLICT (chunk_id) DO UPDATE SET
                            embedding = EXCLUDED.embedding,
                            model = EXCLUDED.model,
                            created_at = NOW()
                        """,
                        chunk_id,
                        embedding,
                        model,
                    )

    async def save_scrape_state(
        self, scrape_type: str, last_continue: str, total: int, scraped: int, status: str
    ) -> None:
        """Save scraping progress for resume capability."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO scrape_state (scrape_type, last_continue, total_pages, pages_scraped, status, updated_at)
                VALUES ($1, $2, $3, $4, $5, NOW())
                ON CONFLICT (id) DO UPDATE SET
                    last_continue = EXCLUDED.last_continue,
                    pages_scraped = EXCLUDED.pages_scraped,
                    status = EXCLUDED.status,
                    updated_at = NOW(),
                    completed_at = CASE WHEN EXCLUDED.status = 'completed' THEN NOW() ELSE NULL END
                """,
                scrape_type,
                last_continue,
                total,
                scraped,
                status,
            )

    async def get_scrape_state(self, scrape_type: str) -> dict | None:
        """Get the most recent in-progress scrape state for resume capability."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT last_continue, pages_scraped, total_pages, status, updated_at
                FROM scrape_state
                WHERE scrape_type = $1 AND status = 'in_progress'
                ORDER BY updated_at DESC
                LIMIT 1
                """,
                scrape_type,
            )
            if row is None:
                return None
            return {
                "last_continue": row["last_continue"],
                "pages_scraped": row["pages_scraped"],
                "total_pages": row["total_pages"],
                "status": row["status"],
                "updated_at": row["updated_at"],
            }

    async def get_unembedded_chunks(self, batch_size: int = 500) -> list[dict]:
        """Get chunks that don't have embeddings yet."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT c.id, c.content
                FROM wiki_chunks c
                LEFT JOIN wiki_embeddings e ON e.chunk_id = c.id
                WHERE e.id IS NULL
                ORDER BY c.id
                LIMIT $1
                """,
                batch_size,
            )
            return [{"id": row["id"], "content": row["content"]} for row in rows]

    async def batch_upsert_embeddings(
        self, chunk_ids: list[int], embeddings: list[list[float]], model: str
    ) -> None:
        """Store embeddings in batch using executemany for speed."""
        async with self.pool.acquire() as conn:
            await conn.executemany(
                """
                INSERT INTO wiki_embeddings (chunk_id, embedding, model)
                VALUES ($1, $2, $3)
                ON CONFLICT (chunk_id) DO UPDATE SET
                    embedding = EXCLUDED.embedding,
                    model = EXCLUDED.model,
                    created_at = NOW()
                """,
                [(cid, emb, model) for cid, emb in zip(chunk_ids, embeddings)],
            )

    async def get_stats(self) -> dict:
        """Get current database statistics."""
        async with self.pool.acquire() as conn:
            pages = await conn.fetchval("SELECT COUNT(*) FROM wiki_pages")
            chunks = await conn.fetchval("SELECT COUNT(*) FROM wiki_chunks")
            embeddings = await conn.fetchval("SELECT COUNT(*) FROM wiki_embeddings")
            return {
                "pages": pages,
                "chunks": chunks,
                "embeddings": embeddings,
            }
