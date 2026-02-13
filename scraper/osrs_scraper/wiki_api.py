"""
MediaWiki API client for the OSRS Wiki.

Uses the wiki's built-in API to fetch page content — cleaner and more
efficient than HTML scraping. The API returns structured data with
parsed content, categories, and metadata.
"""

import asyncio
import hashlib
import logging
import time
from dataclasses import dataclass, field

import httpx

logger = logging.getLogger(__name__)

API_URL = "https://oldschool.runescape.wiki/api.php"
USER_AGENT = "WiseOldManAi/1.0 (OSRS AI assistant; contact@wiseoldman.ai)"

# Concurrency: 3 simultaneous requests with small delay between
MAX_CONCURRENT = 3
REQUEST_DELAY = 0.35  # ~3 requests/sec total


@dataclass
class WikiPage:
    page_id: int
    title: str
    content: str
    categories: list[str] = field(default_factory=list)
    page_type: str = "general"
    url: str = ""
    last_modified: str = ""
    content_hash: str = ""

    def __post_init__(self):
        if not self.content_hash:
            self.content_hash = hashlib.sha256(self.content.encode()).hexdigest()
        if not self.url:
            safe_title = self.title.replace(" ", "_")
            self.url = f"https://oldschool.runescape.wiki/w/{safe_title}"


class OsrsWikiClient:
    """Async client for the OSRS Wiki MediaWiki API."""

    def __init__(self):
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers={"User-Agent": USER_AGENT},
        )
        self._semaphore = asyncio.Semaphore(MAX_CONCURRENT)
        self._last_request_time = 0.0
        self._lock = asyncio.Lock()

    async def close(self):
        await self.client.aclose()

    async def _rate_limit(self):
        """Enforce rate limiting between requests."""
        async with self._lock:
            elapsed = time.time() - self._last_request_time
            if elapsed < REQUEST_DELAY:
                await asyncio.sleep(REQUEST_DELAY - elapsed)
            self._last_request_time = time.time()

    async def _api_request(self, params: dict) -> dict:
        """Make a rate-limited request to the MediaWiki API."""
        await self._rate_limit()
        params["format"] = "json"

        for attempt in range(3):
            try:
                response = await self.client.get(API_URL, params=params)
                response.raise_for_status()
                return response.json()
            except (httpx.HTTPError, httpx.TimeoutException) as e:
                logger.warning(f"Request failed (attempt {attempt + 1}/3): {e}")
                if attempt < 2:
                    await asyncio.sleep(2 ** attempt)
                else:
                    raise

    async def get_all_page_ids(self, callback=None, skip_redirects=True) -> list[dict]:
        """
        Enumerate all articles in the main namespace (ns=0).
        Returns list of {pageid, title} dicts.

        Args:
            callback: Progress callback(count, batch_num)
            skip_redirects: If True, only return real content pages (no redirects)
        """
        all_pages = []
        params = {
            "action": "query",
            "list": "allpages",
            "apnamespace": "0",
            "aplimit": "500",
        }
        if skip_redirects:
            params["apfilterredir"] = "nonredirects"

        batch_num = 0
        while True:
            data = await self._api_request(params)
            pages = data.get("query", {}).get("allpages", [])
            all_pages.extend(pages)

            batch_num += 1
            if callback:
                callback(len(all_pages), batch_num)

            # Check for continuation
            if "continue" in data:
                params["apcontinue"] = data["continue"]["apcontinue"]
            else:
                break

        logger.info(f"Found {len(all_pages)} articles in main namespace (redirects skipped: {skip_redirects})")
        return all_pages

    async def get_page_content(self, page_id: int) -> WikiPage | None:
        """
        Fetch parsed content for a single page using action=parse.
        Returns a WikiPage with clean text content.
        Uses semaphore for concurrency control.
        """
        async with self._semaphore:
            params = {
                "action": "parse",
                "pageid": str(page_id),
                "prop": "text|categories|revid",
                "disablelimitreport": "true",
                "disableeditsection": "true",
                "disabletoc": "true",
            }

            try:
                data = await self._api_request(params)
            except Exception as e:
                logger.error(f"Failed to fetch page {page_id}: {e}")
                return None

            parse = data.get("parse", {})
            if not parse:
                return None

            title = parse.get("title", "")
            html_content = parse.get("text", {}).get("*", "")
            categories = [
                cat.get("*", "").replace("_", " ")
                for cat in parse.get("categories", [])
            ]

            # Clean HTML to text
            content = self._html_to_text(html_content)

            if not content.strip():
                return None

            page_type = self._classify_page(title, categories)

            return WikiPage(
                page_id=page_id,
                title=title,
                content=content,
                categories=categories,
                page_type=page_type,
            )

    async def get_page_content_batch(self, page_ids: list[int]) -> list[WikiPage]:
        """Fetch content for multiple pages concurrently."""
        tasks = [self.get_page_content(pid) for pid in page_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        pages = []
        for r in results:
            if isinstance(r, WikiPage):
                pages.append(r)
            elif isinstance(r, Exception):
                logger.error(f"Batch fetch error: {r}")
        return pages

    async def get_recent_changes(self, since: str, limit: int = 500) -> list[dict]:
        """
        Get pages modified since a given timestamp.
        Used for incremental updates.

        Args:
            since: ISO timestamp (e.g., "2026-02-12T00:00:00Z")
            limit: Max changes to return per request
        """
        all_changes = []
        params = {
            "action": "query",
            "list": "recentchanges",
            "rcnamespace": "0",
            "rcprop": "title|ids|timestamp",
            "rclimit": str(limit),
            "rcend": since,
            "rctype": "edit|new",
        }

        while True:
            data = await self._api_request(params)
            changes = data.get("query", {}).get("recentchanges", [])
            all_changes.extend(changes)

            if "continue" in data:
                params["rccontinue"] = data["continue"]["rccontinue"]
            else:
                break

        # Deduplicate by page_id
        seen = set()
        unique_changes = []
        for change in all_changes:
            pid = change.get("pageid")
            if pid not in seen:
                seen.add(pid)
                unique_changes.append(change)

        logger.info(f"Found {len(unique_changes)} changed pages since {since}")
        return unique_changes

    def _html_to_text(self, html: str) -> str:
        """Convert MediaWiki HTML output to clean text, preserving structure."""
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "lxml")

        # Remove unwanted elements
        for tag in soup.find_all(["script", "style"]):
            tag.decompose()

        # Remove reference markers
        for tag in soup.find_all("sup"):
            classes = tag.get("class") or []
            if "reference" in classes:
                tag.decompose()

        for tag in soup.find_all("span"):
            classes = tag.get("class") or []
            if "reference" in classes:
                tag.decompose()

        # Remove navigation boxes, see-also, external links sections
        for tag in soup.find_all("div", class_=["navbox", "ambox", "mbox"]):
            tag.decompose()

        # Remove [edit] links
        for tag in soup.find_all("span", class_="mw-editsection"):
            tag.decompose()

        # Build structured text preserving headers
        parts = []
        for element in soup.find_all(["h2", "h3", "h4", "p", "li", "th", "td", "dd"]):
            text = element.get_text(separator=" ", strip=True)
            if not text:
                continue

            if element.name in ("h2", "h3", "h4"):
                parts.append(f"\n## {text}\n")
            elif element.name == "li":
                parts.append(f"- {text}")
            else:
                parts.append(text)

        return "\n".join(parts).strip()

    def _classify_page(self, title: str, categories: list[str]) -> str:
        """Classify a wiki page into a type based on title and categories."""
        cats_lower = [c.lower() for c in categories]
        title_lower = title.lower()

        if any("quest" in c for c in cats_lower):
            return "quest"
        elif any("monster" in c and "category" not in c for c in cats_lower):
            return "monster"
        elif any("boss" in c for c in cats_lower):
            return "boss"
        elif any("item" in c and "category" not in c for c in cats_lower):
            return "item"
        elif any("equipment" in c for c in cats_lower):
            return "equipment"
        elif any("weapon" in c for c in cats_lower):
            return "equipment"
        elif any("armour" in c or "armor" in c for c in cats_lower):
            return "equipment"
        elif any("skill" in c and "guide" not in c for c in cats_lower):
            return "skill"
        elif any("location" in c or "city" in c or "town" in c for c in cats_lower):
            return "location"
        elif any("minigame" in c for c in cats_lower):
            return "minigame"
        elif any("npc" in c for c in cats_lower):
            return "npc"
        elif any("spell" in c or "prayer" in c for c in cats_lower):
            return "spell"
        elif any("clue" in c for c in cats_lower):
            return "clue"
        elif "money making" in title_lower:
            return "money_making"
        elif any("achievement" in c or "diary" in c for c in cats_lower):
            return "achievement_diary"
        else:
            return "general"
