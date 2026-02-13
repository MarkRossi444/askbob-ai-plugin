#!/usr/bin/env python3
"""Live embedding progress monitor. Polls DB every 15s and prints a progress bar."""
import asyncio, os, sys, time
from dotenv import load_dotenv
load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from processing.db import WikiDatabase

async def main():
    db = WikiDatabase()
    await db.connect()
    s = await db.get_stats()
    initial = s["embeddings"]
    start = time.time()
    try:
        while True:
            stats = await db.get_stats()
            total = stats["chunks"]
            done = stats["embeddings"]
            if total == 0:
                sys.stdout.write("Waiting for chunks...\n")
                sys.stdout.flush()
                await asyncio.sleep(10)
                continue
            pct = done / total * 100
            filled = int(40 * done / total)
            bar = "\u2588" * filled + "\u2591" * (40 - filled)
            new = done - initial
            elapsed = time.time() - start
            rate = new / elapsed if elapsed > 0 and new > 0 else 0
            remaining = total - done
            eta = remaining / rate / 60 if rate > 0 else 0
            sys.stdout.write(f"  [{bar}] {pct:5.1f}%  {done:,}/{total:,}  ({rate:.0f}/s, ETA {eta:.0f}m)\n")
            sys.stdout.flush()
            if done >= total:
                sys.stdout.write("\n  Embeddings complete!\n")
                sys.stdout.flush()
                break
            await asyncio.sleep(15)
    finally:
        await db.close()

asyncio.run(main())
