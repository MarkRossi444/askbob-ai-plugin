"""
Embedding pipeline for OSRS wiki chunks.

Generates vector embeddings using OpenAI's text-embedding-3-small model.
Processes chunks in batches for efficiency and stores results in pgvector.
"""

import asyncio
import logging
import os
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
EMBEDDING_DIMENSION = 1536
OPENAI_API_URL = "https://api.openai.com/v1/embeddings"
BATCH_SIZE = 100  # OpenAI allows up to 2048 inputs per request


@dataclass
class EmbeddingResult:
    chunk_id: int
    embedding: list[float]
    model: str


class EmbeddingClient:
    """Client for generating text embeddings via OpenAI API."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("EMBEDDING_API_KEY", "")
        if not self.api_key:
            raise ValueError(
                "Embedding API key required. Set EMBEDDING_API_KEY env var "
                "or pass api_key parameter."
            )
        self.client = httpx.AsyncClient(
            timeout=60.0,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )
        self.model = EMBEDDING_MODEL

    async def close(self):
        await self.client.aclose()

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for a list of texts.
        Handles batching automatically for large inputs.
        """
        all_embeddings = []

        for i in range(0, len(texts), BATCH_SIZE):
            batch = texts[i:i + BATCH_SIZE]
            embeddings = await self._embed_batch(batch)
            all_embeddings.extend(embeddings)

            if i + BATCH_SIZE < len(texts):
                logger.info(
                    f"Embedded {i + len(batch)}/{len(texts)} texts"
                )
                await asyncio.sleep(0.5)  # Rate limiting

        return all_embeddings

    async def embed_single(self, text: str) -> list[float]:
        """Generate embedding for a single text."""
        results = await self._embed_batch([text])
        return results[0]

    async def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Send a batch of texts to the embedding API."""
        # Truncate very long texts (model max is ~8191 tokens)
        truncated = [t[:32000] for t in texts]

        payload = {
            "input": truncated,
            "model": self.model,
            "dimensions": EMBEDDING_DIMENSION,
        }

        for attempt in range(3):
            try:
                response = await self.client.post(OPENAI_API_URL, json=payload)
                response.raise_for_status()
                data = response.json()

                # Sort by index to maintain order
                sorted_data = sorted(data["data"], key=lambda x: x["index"])
                return [item["embedding"] for item in sorted_data]

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    wait = 2 ** attempt * 5
                    logger.warning(f"Rate limited. Waiting {wait}s...")
                    await asyncio.sleep(wait)
                else:
                    logger.error(f"Embedding API error: {e.response.text}")
                    raise
            except Exception as e:
                logger.error(f"Embedding failed (attempt {attempt + 1}): {e}")
                if attempt < 2:
                    await asyncio.sleep(2 ** attempt)
                else:
                    raise

        return []
