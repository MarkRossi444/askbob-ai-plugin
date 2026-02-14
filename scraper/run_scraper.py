#!/usr/bin/env python3
"""
AskBob.Ai — OSRS Wiki Scraping Pipeline

Main entry point for scraping the entire OSRS wiki, processing content
into chunks, generating embeddings, and storing everything in PostgreSQL.

Usage:
    # Full scrape (first time)
    python run_scraper.py --full

    # Incremental update (daily)
    python run_scraper.py --update

    # Just scrape pages (no embedding)
    python run_scraper.py --full --skip-embed

    # Generate embeddings for scraped chunks
    python run_scraper.py --embed-only

    # Resume an interrupted full scrape
    python run_scraper.py --full --resume

    # Check stats
    python run_scraper.py --stats
"""

import argparse
import asyncio
import logging
import os
import shutil
import sys
import time
from datetime import datetime, timezone, timedelta

from dotenv import load_dotenv

# Add parent dir to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from osrs_scraper.wiki_api import OsrsWikiClient
from processing.chunker import chunk_page
from processing.embedder import EmbeddingClient
from processing.db import WikiDatabase

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("scraper")

# Process pages in batches of this size for concurrency
BATCH_SIZE = 10


def progress_bar(current: int, total: int, *, rate: float = 0, eta_min: float = 0, label: str = ""):
    """Print a terminal progress bar that overwrites the current line."""
    if total == 0:
        return
    term_width = shutil.get_terminal_size((80, 20)).columns
    pct = current / total
    pct_str = f"{pct * 100:5.1f}%"
    stats = f" {current:,}/{total:,}"
    if rate > 0:
        stats += f" [{rate:.1f}/s, ETA {eta_min:.0f}m]"
    if label:
        stats = f" {label}{stats}"
    # Calculate bar width from remaining space: "  [=====>    ] 100.0% stats"
    overhead = 2 + 1 + 1 + 1 + len(pct_str) + len(stats)  # spacing + brackets + pct + stats
    bar_width = max(10, term_width - overhead)
    filled = int(bar_width * pct)
    arrow = ">" if filled < bar_width else ""
    bar = "=" * max(0, filled - 1) + arrow + " " * (bar_width - filled)
    line = f"\r  [{bar}] {pct_str}{stats}"
    sys.stdout.write(line)
    sys.stdout.flush()
    if current >= total:
        sys.stdout.write("\n")
        sys.stdout.flush()


async def process_page(wiki, db, embed_client, page_info):
    """Process a single page: fetch, chunk, store, embed."""
    page_id = page_info["pageid"]
    title = page_info["title"]

    try:
        page = await wiki.get_page_content(page_id)
        if not page:
            return "skipped", 0

        if not await db.page_needs_update(page_id, page.content_hash):
            return "skipped", 0

        await db.upsert_page(page)

        chunks = chunk_page(
            page_id=page.page_id,
            title=page.title,
            content=page.content,
            page_type=page.page_type,
            categories=page.categories,
        )

        if not chunks:
            return "skipped", 0

        chunk_ids = await db.upsert_chunks(chunks)

        if embed_client and chunk_ids:
            texts = [c.content for c in chunks]
            embeddings = await embed_client.embed_texts(texts)
            await db.upsert_embeddings(chunk_ids, embeddings, embed_client.model)

        return "scraped", len(chunks)

    except Exception as e:
        logger.error(f"Error processing '{title}' (id={page_id}): {e}")
        return "error", 0


async def full_scrape(db: WikiDatabase, skip_embed: bool = False, resume: bool = False):
    """
    Full scrape of the entire OSRS wiki.

    Steps:
    1. Enumerate all real content articles (skip redirects)
    2. Fetch content concurrently (3 at a time)
    3. Chunk content into semantic pieces
    4. Generate embeddings (unless skip_embed)
    5. Store everything in PostgreSQL

    If resume=True, attempts to pick up from a previously interrupted scrape.
    """
    wiki = OsrsWikiClient()
    embed_client = None if skip_embed else EmbeddingClient()

    # Check for resume state
    start_offset = 0
    if resume:
        state = await db.get_scrape_state("full")
        if state:
            start_offset = state["pages_scraped"]
            logger.info(
                f"Resuming from page {start_offset}/{state['total_pages']} "
                f"(interrupted at {state['updated_at']})"
            )
        else:
            logger.info("No incomplete scrape found, starting fresh")

    try:
        # Step 1: Get all page IDs (non-redirects only)
        logger.info("Step 1: Enumerating all wiki articles (skipping redirects)...")

        def progress(count, batch):
            if batch % 10 == 0:
                logger.info(f"  Found {count} articles so far...")

        all_pages = await wiki.get_all_page_ids(callback=progress, skip_redirects=True)
        total = len(all_pages)
        logger.info(f"Found {total} real content articles to scrape")

        # If resuming, skip already-processed pages
        if start_offset > 0 and start_offset < total:
            logger.info(f"Skipping first {start_offset} pages (already processed)")
            all_pages = all_pages[start_offset:]
            total_remaining = len(all_pages)
        else:
            start_offset = 0
            total_remaining = total

        # Save initial state
        await db.save_scrape_state("full", "", total, start_offset, "in_progress")

        # Step 2-5: Process pages in concurrent batches
        scraped = 0
        skipped = 0
        errors = 0
        total_chunks = 0
        start_time = time.time()

        for i in range(0, total_remaining, BATCH_SIZE):
            batch = all_pages[i:i + BATCH_SIZE]

            # Fire off batch concurrently
            tasks = [
                process_page(wiki, db, embed_client, page_info)
                for page_info in batch
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in results:
                if isinstance(result, Exception):
                    errors += 1
                    logger.error(f"Batch error: {result}")
                else:
                    status, chunks = result
                    if status == "scraped":
                        scraped += 1
                        total_chunks += chunks
                    elif status == "skipped":
                        skipped += 1
                    else:
                        errors += 1

            # Progress logging
            processed = min(i + BATCH_SIZE, total_remaining)
            absolute_processed = start_offset + processed

            # Save progress every 500 pages
            if processed % 500 < BATCH_SIZE:
                await db.save_scrape_state(
                    "full", str(absolute_processed), total, absolute_processed, "in_progress"
                )

            elapsed = time.time() - start_time
            rate = processed / elapsed if elapsed > 0 else 0
            eta = (total_remaining - processed) / rate if rate > 0 else 0
            progress_bar(absolute_processed, total, rate=rate, eta_min=eta / 60, label="Scraping")

            if processed % 100 < BATCH_SIZE:
                logger.info(
                    f"Progress: {absolute_processed}/{total} "
                    f"({scraped} scraped, {skipped} skipped, {errors} errors) "
                    f"[{rate:.1f} pages/s, ETA: {eta / 60:.0f}m] "
                    f"[{total_chunks} chunks]"
                )

        # Mark as completed
        await db.save_scrape_state("full", "", total, total, "completed")

        elapsed = time.time() - start_time
        logger.info(
            f"\nFull scrape complete!\n"
            f"  Total articles: {total}\n"
            f"  Scraped: {scraped}\n"
            f"  Skipped (empty/unchanged): {skipped}\n"
            f"  Errors: {errors}\n"
            f"  Total chunks: {total_chunks}\n"
            f"  Time: {elapsed / 60:.1f} minutes"
        )

    finally:
        await wiki.close()
        if embed_client:
            await embed_client.close()


async def incremental_update(db: WikiDatabase):
    """
    Fetch only pages that have changed since the last scrape.
    Uses the MediaWiki Recent Changes API.
    """
    wiki = OsrsWikiClient()
    embed_client = EmbeddingClient()

    try:
        # Look back 24 hours by default
        since = (datetime.now(timezone.utc) - timedelta(hours=24)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )

        logger.info(f"Checking for changes since {since}...")
        changes = await wiki.get_recent_changes(since)

        if not changes:
            logger.info("No changes found. Wiki data is current.")
            return

        logger.info(f"Found {len(changes)} changed pages. Updating...")

        updated = 0
        errors = 0
        total_chunks = 0

        for change in changes:
            page_id = change["pageid"]
            title = change.get("title", "Unknown")

            try:
                page = await wiki.get_page_content(page_id)
                if not page:
                    continue

                # Check if content actually changed
                if not await db.page_needs_update(page_id, page.content_hash):
                    continue

                await db.upsert_page(page)

                chunks = chunk_page(
                    page_id=page.page_id,
                    title=page.title,
                    content=page.content,
                    page_type=page.page_type,
                    categories=page.categories,
                )

                if chunks:
                    chunk_ids = await db.upsert_chunks(chunks)
                    total_chunks += len(chunks)

                    texts = [c.content for c in chunks]
                    embeddings = await embed_client.embed_texts(texts)
                    await db.upsert_embeddings(chunk_ids, embeddings, embed_client.model)

                updated += 1
                logger.info(f"Updated: {title} ({len(chunks)} chunks)")

            except Exception as e:
                logger.error(f"Error updating '{title}': {e}")
                errors += 1

        logger.info(
            f"\nIncremental update complete!\n"
            f"  Changed pages found: {len(changes)}\n"
            f"  Actually updated: {updated}\n"
            f"  Errors: {errors}\n"
            f"  New chunks: {total_chunks}"
        )

    finally:
        await wiki.close()
        await embed_client.close()


async def embed_only(db: WikiDatabase):
    """
    Generate embeddings for all chunks that don't have them yet.
    Useful after running a scrape with --skip-embed.
    """
    embed_client = EmbeddingClient()
    EMBED_FETCH_BATCH = 500  # Chunks to fetch from DB at once
    EMBED_API_BATCH = 100    # Chunks to send to OpenAI at once

    try:
        stats = await db.get_stats()
        total_unembedded = stats["chunks"] - stats["embeddings"]
        logger.info(
            f"Embedding pipeline: {stats['chunks']} chunks, "
            f"{stats['embeddings']} already embedded, "
            f"{total_unembedded} remaining"
        )

        if total_unembedded == 0:
            logger.info("All chunks already have embeddings. Nothing to do.")
            return

        embedded_total = 0
        start_time = time.time()

        while True:
            # Fetch next batch of unembedded chunks
            unembedded = await db.get_unembedded_chunks(batch_size=EMBED_FETCH_BATCH)
            if not unembedded:
                break

            # Process in smaller API batches
            for i in range(0, len(unembedded), EMBED_API_BATCH):
                batch = unembedded[i:i + EMBED_API_BATCH]
                chunk_ids = [c["id"] for c in batch]
                texts = [c["content"] for c in batch]

                embeddings = await embed_client.embed_texts(texts)
                await db.batch_upsert_embeddings(chunk_ids, embeddings, embed_client.model)

                embedded_total += len(batch)
                elapsed = time.time() - start_time
                rate = embedded_total / elapsed if elapsed > 0 else 0
                remaining = total_unembedded - embedded_total
                eta = remaining / rate if rate > 0 else 0

                progress_bar(embedded_total, total_unembedded, rate=rate, eta_min=eta / 60, label="Embedding")

                if embedded_total % 1000 < EMBED_API_BATCH:
                    logger.info(
                        f"Embedded: {embedded_total}/{total_unembedded} "
                        f"[{rate:.1f} chunks/s, ETA: {eta / 60:.1f}m]"
                    )

        elapsed = time.time() - start_time
        logger.info(
            f"\nEmbedding complete!\n"
            f"  Chunks embedded: {embedded_total}\n"
            f"  Time: {elapsed / 60:.1f} minutes\n"
            f"  Rate: {embedded_total / elapsed:.1f} chunks/s"
        )

    finally:
        await embed_client.close()


async def show_stats(db: WikiDatabase):
    """Show current database statistics."""
    stats = await db.get_stats()
    print(f"\nAskBob.Ai Database Stats")
    print(f"{'=' * 35}")
    print(f"  Wiki pages:  {stats['pages']:,}")
    print(f"  Chunks:      {stats['chunks']:,}")
    print(f"  Embeddings:  {stats['embeddings']:,}")
    if stats['chunks'] > 0:
        progress_bar(stats['embeddings'], stats['chunks'], label="Coverage")
    print()


async def main():
    parser = argparse.ArgumentParser(description="AskBob.Ai Wiki Scraper")
    parser.add_argument("--full", action="store_true", help="Full scrape of all wiki articles")
    parser.add_argument("--update", action="store_true", help="Incremental update (last 24h)")
    parser.add_argument("--stats", action="store_true", help="Show database stats")
    parser.add_argument("--skip-embed", action="store_true", help="Skip embedding generation")
    parser.add_argument("--embed-only", action="store_true", help="Generate embeddings for unembedded chunks")
    parser.add_argument("--resume", action="store_true", help="Resume an interrupted --full scrape from where it left off")
    args = parser.parse_args()

    if not any([args.full, args.update, args.stats, args.embed_only]):
        parser.print_help()
        return

    db = WikiDatabase()
    await db.connect()

    try:
        if args.stats:
            await show_stats(db)
        if args.full:
            await full_scrape(db, skip_embed=args.skip_embed, resume=args.resume)
        elif args.update:
            await incremental_update(db)
        if args.embed_only:
            await embed_only(db)
    finally:
        await db.close()


if __name__ == "__main__":
    asyncio.run(main())
