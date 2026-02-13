"""
Content chunker for OSRS wiki pages.

Splits wiki page content into semantically meaningful chunks
based on section headers. Each chunk includes metadata for
filtering during retrieval.
"""

import re
from dataclasses import dataclass, field


@dataclass
class WikiChunk:
    page_id: int
    chunk_index: int
    title: str
    section_header: str
    content: str
    token_count: int
    page_type: str
    categories: list[str] = field(default_factory=list)
    game_modes: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


# Rough token estimation: ~4 chars per token for English
CHARS_PER_TOKEN = 4
MIN_CHUNK_TOKENS = 50
MAX_CHUNK_TOKENS = 1000
OVERLAP_TOKENS = 100

# Keywords that indicate ironman-specific content
IRONMAN_KEYWORDS = [
    "ironman", "iron man", "hardcore", "ultimate ironman",
    "group ironman", "cannot trade", "cannot use the grand exchange",
    "self-sufficient",
]

# Keywords that indicate content is NOT relevant to ironman
MAIN_ONLY_KEYWORDS = [
    "grand exchange price", "buy limit", "trading",
]


def estimate_tokens(text: str) -> int:
    """Rough token count estimation."""
    return len(text) // CHARS_PER_TOKEN


def detect_game_modes(text: str, title: str, categories: list[str]) -> list[str]:
    """Determine which game modes a chunk is relevant to."""
    text_lower = text.lower()
    title_lower = title.lower()
    cats_lower = [c.lower() for c in categories]

    modes = ["main", "ironman", "hardcore_ironman", "ultimate_ironman", "group_ironman"]

    # Check if this is ironman-specific content
    if any(kw in title_lower for kw in ["ironman guide", "ironman", "iron man"]):
        return ["ironman", "hardcore_ironman", "ultimate_ironman", "group_ironman"]

    # Check if content mentions GE trading (not relevant to most ironmen)
    if any(kw in text_lower for kw in MAIN_ONLY_KEYWORDS):
        # Still relevant to GIM (can trade within group) and main
        return ["main", "group_ironman"]

    # Default: relevant to all modes
    return modes


def chunk_page(
    page_id: int,
    title: str,
    content: str,
    page_type: str,
    categories: list[str],
) -> list[WikiChunk]:
    """
    Split a wiki page into semantic chunks based on section headers.

    Strategy:
    1. Split on ## headers (H2/H3 from the wiki)
    2. If a section exceeds MAX_CHUNK_TOKENS, split on paragraph boundaries
    3. If a section is too small, merge with the next section
    4. Add overlap between chunks for context continuity
    """
    if not content.strip():
        return []

    # Split content into sections by headers
    sections = _split_into_sections(content)

    chunks = []
    chunk_index = 0
    buffer_header = title
    buffer_content = ""

    for section_header, section_content in sections:
        header = section_header or title
        text = section_content.strip()

        if not text:
            continue

        # Skip certain sections that aren't useful for Q&A
        if header.lower() in ("references", "external links", "see also", "gallery"):
            continue

        combined = buffer_content + "\n" + text if buffer_content else text
        combined_tokens = estimate_tokens(combined)

        if combined_tokens < MIN_CHUNK_TOKENS:
            # Too small — accumulate into buffer
            buffer_content = combined
            if not buffer_header or buffer_header == title:
                buffer_header = header
            continue

        if combined_tokens <= MAX_CHUNK_TOKENS:
            # Good size — create a chunk
            game_modes = detect_game_modes(combined, title, categories)
            chunks.append(WikiChunk(
                page_id=page_id,
                chunk_index=chunk_index,
                title=title,
                section_header=buffer_header if buffer_content else header,
                content=combined.strip(),
                token_count=combined_tokens,
                page_type=page_type,
                categories=categories,
                game_modes=game_modes,
                metadata={"section": header},
            ))
            chunk_index += 1
            buffer_content = ""
            buffer_header = ""
        else:
            # Too large — flush buffer first, then split this section
            if buffer_content:
                buf_tokens = estimate_tokens(buffer_content)
                if buf_tokens >= MIN_CHUNK_TOKENS:
                    game_modes = detect_game_modes(buffer_content, title, categories)
                    chunks.append(WikiChunk(
                        page_id=page_id,
                        chunk_index=chunk_index,
                        title=title,
                        section_header=buffer_header,
                        content=buffer_content.strip(),
                        token_count=buf_tokens,
                        page_type=page_type,
                        categories=categories,
                        game_modes=game_modes,
                        metadata={"section": buffer_header},
                    ))
                    chunk_index += 1
                buffer_content = ""
                buffer_header = ""

            # Split the large section into sub-chunks
            sub_chunks = _split_large_text(text, MAX_CHUNK_TOKENS, OVERLAP_TOKENS)
            for sub in sub_chunks:
                sub_tokens = estimate_tokens(sub)
                if sub_tokens >= MIN_CHUNK_TOKENS:
                    game_modes = detect_game_modes(sub, title, categories)
                    chunks.append(WikiChunk(
                        page_id=page_id,
                        chunk_index=chunk_index,
                        title=title,
                        section_header=header,
                        content=sub.strip(),
                        token_count=sub_tokens,
                        page_type=page_type,
                        categories=categories,
                        game_modes=game_modes,
                        metadata={"section": header},
                    ))
                    chunk_index += 1

    # Flush any remaining buffer
    if buffer_content.strip():
        buf_tokens = estimate_tokens(buffer_content)
        if buf_tokens >= MIN_CHUNK_TOKENS:
            game_modes = detect_game_modes(buffer_content, title, categories)
            chunks.append(WikiChunk(
                page_id=page_id,
                chunk_index=chunk_index,
                title=title,
                section_header=buffer_header or title,
                content=buffer_content.strip(),
                token_count=buf_tokens,
                page_type=page_type,
                categories=categories,
                game_modes=game_modes,
                metadata={"section": buffer_header or title},
            ))

    # Prepend page title context to each chunk for better retrieval
    for chunk in chunks:
        prefix = f"Page: {title}"
        if chunk.section_header and chunk.section_header != title:
            prefix += f" | Section: {chunk.section_header}"
        prefix += f" | Type: {page_type}\n\n"
        chunk.content = prefix + chunk.content
        chunk.token_count = estimate_tokens(chunk.content)

    return chunks


def _split_into_sections(content: str) -> list[tuple[str, str]]:
    """Split content by ## headers into (header, content) pairs."""
    # Pattern matches lines starting with ## (wiki section headers)
    pattern = r"^##\s+(.+)$"
    parts = re.split(pattern, content, flags=re.MULTILINE)

    sections = []
    if parts[0].strip():
        # Content before the first header (intro section)
        sections.append(("", parts[0].strip()))

    # Pair up headers with their content
    for i in range(1, len(parts), 2):
        header = parts[i].strip() if i < len(parts) else ""
        body = parts[i + 1].strip() if i + 1 < len(parts) else ""
        if header or body:
            sections.append((header, body))

    return sections


def _split_large_text(
    text: str,
    max_tokens: int,
    overlap_tokens: int,
) -> list[str]:
    """Split a large text block on paragraph boundaries with overlap."""
    paragraphs = text.split("\n")
    chunks = []
    current_chunk = []
    current_tokens = 0

    for para in paragraphs:
        para_tokens = estimate_tokens(para)

        if current_tokens + para_tokens > max_tokens and current_chunk:
            chunks.append("\n".join(current_chunk))

            # Keep last few paragraphs for overlap
            overlap_text = ""
            overlap_paras = []
            for p in reversed(current_chunk):
                if estimate_tokens(overlap_text + p) > overlap_tokens:
                    break
                overlap_paras.insert(0, p)
                overlap_text = "\n".join(overlap_paras)

            current_chunk = overlap_paras
            current_tokens = estimate_tokens(overlap_text)

        current_chunk.append(para)
        current_tokens += para_tokens

    if current_chunk:
        chunks.append("\n".join(current_chunk))

    return chunks
