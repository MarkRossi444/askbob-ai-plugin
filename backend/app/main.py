"""
WiseOldMan.Ai — FastAPI Backend

Main application entry point. Sets up the database pool, RAG pipeline,
and API routes. The RAG pipeline is initialized once at startup and
shared across all requests.
"""

import logging
import os
import time
from collections import deque
from contextlib import asynccontextmanager

import asyncpg
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pgvector.asyncpg import register_vector

from app.config import settings
from app.core.rag_pipeline import RagPipeline
from app.core.stats_tracker import StatsTracker
from app.api.routes.chat import router as chat_router
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.request_logging import RequestLoggingMiddleware

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# Global reference — initialized on startup
_rag_pipeline: RagPipeline | None = None
_stats_tracker: StatsTracker | None = None
_startup_time: float = 0.0

# Track last 100 chat response times for avg_response_time_ms
response_times: deque[float] = deque(maxlen=100)


def get_rag_pipeline() -> RagPipeline:
    """Get the RAG pipeline instance. Called by route handlers."""
    if _rag_pipeline is None:
        raise RuntimeError("RAG pipeline not initialized")
    return _rag_pipeline


def get_stats_tracker() -> StatsTracker:
    """Get the stats tracker instance. Called by middleware and routes."""
    if _stats_tracker is None:
        raise RuntimeError("Stats tracker not initialized")
    return _stats_tracker


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle — creates DB pool and RAG pipeline."""
    global _rag_pipeline, _stats_tracker, _startup_time

    _startup_time = time.time()
    _stats_tracker = StatsTracker()
    logger.info("Starting WiseOldMan.Ai backend...")

    # Create database connection pool with pgvector registered on every connection
    async def _init_conn(conn):
        await register_vector(conn)

    pool = await asyncpg.create_pool(
        settings.database_url,
        min_size=2,
        max_size=10,
        init=_init_conn,
    )

    logger.info("Database connected")

    # Initialize RAG pipeline
    _rag_pipeline = RagPipeline(pool)
    logger.info("RAG pipeline ready")

    yield

    # Shutdown
    logger.info("Shutting down...")
    await _rag_pipeline.close()
    await pool.close()
    _rag_pipeline = None


app = FastAPI(
    title="WiseOldMan.Ai API",
    description="AI-powered OSRS expert chatbot backend",
    version="0.1.0",
    lifespan=lifespan,
)

# Middleware — order matters: outermost runs first
# 1. Request logging (outermost — logs everything including rate-limited requests)
app.add_middleware(RequestLoggingMiddleware)
# 2. Rate limiting
app.add_middleware(RateLimitMiddleware)
# 3. CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.allowed_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(chat_router, prefix="/api")


def _format_uptime(seconds: float) -> str:
    """Format seconds into human-readable uptime like '2h 15m'."""
    s = int(seconds)
    if s < 60:
        return f"{s}s"
    if s < 3600:
        return f"{s // 60}m {s % 60}s"
    hours = s // 3600
    minutes = (s % 3600) // 60
    return f"{hours}h {minutes}m"


@app.get("/api/health")
async def health_check():
    stats = {"pages": 0, "chunks": 0, "embeddings": 0}
    if _rag_pipeline and _rag_pipeline.pool:
        try:
            async with _rag_pipeline.pool.acquire() as conn:
                stats["pages"] = await conn.fetchval("SELECT COUNT(*) FROM wiki_pages")
                stats["chunks"] = await conn.fetchval("SELECT COUNT(*) FROM wiki_chunks")
                stats["embeddings"] = await conn.fetchval("SELECT COUNT(*) FROM wiki_embeddings")
        except Exception:
            pass

    # Embedding coverage
    coverage_pct = 0.0
    if stats["chunks"] > 0:
        coverage_pct = round((stats["embeddings"] / stats["chunks"]) * 100, 1)

    # Uptime
    uptime_seconds = round(time.time() - _startup_time, 1) if _startup_time else 0
    uptime_human = _format_uptime(uptime_seconds)

    # Avg response time
    avg_response_time_ms = round(sum(response_times) / len(response_times), 1) if response_times else 0

    return {
        "status": "ok",
        "service": "WiseOldMan.Ai",
        "rag_ready": _rag_pipeline is not None and stats["embeddings"] > 0,
        "stats": stats,
        "embedding_coverage_pct": coverage_pct,
        "uptime_seconds": uptime_seconds,
        "uptime_human": uptime_human,
        "avg_response_time_ms": avg_response_time_ms,
    }


@app.get("/api/stats")
async def stats():
    if _stats_tracker is None:
        return {"error": "Stats tracker not initialized"}
    return _stats_tracker.get_stats()


# Test chat UI
static_dir = os.path.join(os.path.dirname(__file__), "static")


app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/test")
async def test_page():
    return FileResponse(os.path.join(static_dir, "test.html"))
