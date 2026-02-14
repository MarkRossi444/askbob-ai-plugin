"""
Claude API client for generating chat responses.

Wraps the Anthropic SDK to provide OSRS-expert responses grounded
in wiki context retrieved by the vector search.
"""

import logging
from collections.abc import AsyncGenerator

import anthropic

from app.config import settings

logger = logging.getLogger(__name__)

# Haiku for quick factual lookups, Sonnet for complex reasoning
MODEL_QUICK = "claude-haiku-4-5-20251001"
MODEL_DEEP = "claude-sonnet-4-5-20250929"

SYSTEM_PROMPT = """You are the Wise Old Man from Draynor Village — the legendary retired adventurer and OSRS expert. You've completed every quest, mastered every skill, and even robbed the Draynor bank that one time (you don't like to talk about it). Players come to you for guidance.

Personality:
- Speak with the confidence of someone who's been there and done it all
- Occasionally reference your own adventuring past ("Back when I cleared the TzHaar Fight Caves..." or "I've seen many adventurers struggle with this")
- Be warm but direct. No filler — players are asking mid-game and want answers fast
- Use OSRS terminology naturally: "spec", "DPS", "tick manipulation", "welfare gear", "sweaty", "afk", "GP/hr"
- A touch of dry humor when appropriate, but never at the expense of being helpful

Formatting:
- Use **bold** for item names, quest names, boss names, and important keywords
- Use bullet points for lists (steps, requirements, drop tables)
- Use headers (###) to organize longer answers into sections
- Include specific numbers when you have them: levels, GP amounts, drop rates (1/512), DPS values
- Keep answers concise. 2-4 short paragraphs max for simple questions. Use lists for complex ones

Rules:
- Ground your answers in the wiki context provided. If the context doesn't cover it, say so and suggest the wiki
- NEVER fabricate drop rates, stats, requirements, or GP values — only state what's in the context
- When the player's game mode matters (ironman, hardcore, etc.), tailor every suggestion to their restrictions
- For quest questions, give step-by-step guidance with requirements upfront
- For gear/loadout questions, consider budget tiers (welfare → mid-level → BIS)
- If this is a follow-up question in a conversation, reference what was discussed before naturally"""

GAME_MODE_CONTEXT = {
    "main": "The player is on a regular main account. They have access to the Grand Exchange and can trade freely with other players.",
    "ironman": "The player is an Ironman. They CANNOT trade with other players or use the Grand Exchange. All items must be self-obtained. Adjust all advice accordingly — no 'just buy it on the GE' suggestions.",
    "hardcore_ironman": "The player is a Hardcore Ironman. Same restrictions as Ironman (no trading, no GE), PLUS they lose their hardcore status on death. Prioritize SAFE methods and warn about death risks.",
    "ultimate_ironman": "The player is an Ultimate Ironman. Same as Ironman but they also CANNOT use banks. All items must be carried or stored via alternatives (STASH units, death storage, POH). This fundamentally changes strategy for nearly everything.",
    "group_ironman": "The player is a Group Ironman. They can trade with their group members but NOT other players. They can use a shared group storage. They have limited GE access for some items.",
}


ACCOUNT_TYPE_MAP = {
    "NORMAL": "main",
    "IRONMAN": "ironman",
    "HARDCORE_IRONMAN": "hardcore_ironman",
    "ULTIMATE_IRONMAN": "ultimate_ironman",
    "GROUP_IRONMAN": "group_ironman",
    "HARDCORE_GROUP_IRONMAN": "group_ironman",
    "UNRANKED_GROUP_IRONMAN": "group_ironman",
}


def _account_type_to_game_mode(account_type: str) -> str | None:
    """Map a RuneLite AccountType name to a backend game_mode string."""
    return ACCOUNT_TYPE_MAP.get(account_type)


def _format_player_context(ctx: dict) -> str:
    """
    Format player context dict into a compact, human-readable text block
    that Claude can reference naturally in its responses.
    """
    lines = []

    # Header line: Account | Combat | Total
    header_parts = []
    if "account_type" in ctx:
        header_parts.append(f"Account: {ctx['account_type']}")
    if "player_name" in ctx:
        header_parts.append(f"Player: {ctx['player_name']}")
    if "combat_level" in ctx:
        header_parts.append(f"Combat: {ctx['combat_level']}")
    if "total_level" in ctx:
        header_parts.append(f"Total Level: {ctx['total_level']}")
    if header_parts:
        lines.append(" | ".join(header_parts))

    # Skills — compact single line per skill
    skills = ctx.get("skills")
    if skills and isinstance(skills, dict):
        skill_parts = []
        for name, data in skills.items():
            if isinstance(data, dict) and "level" in data:
                skill_parts.append(f"{name.capitalize()} {data['level']}")
            elif isinstance(data, (int, float)):
                skill_parts.append(f"{name.capitalize()} {int(data)}")
        if skill_parts:
            lines.append(f"Skills: {', '.join(skill_parts)}")

    # Quests completed
    completed = ctx.get("quests_completed")
    if completed and isinstance(completed, list):
        count = len(completed)
        # Show up to 30 quest names to keep payload reasonable
        if count <= 30:
            quest_list = ", ".join(completed)
        else:
            quest_list = ", ".join(completed[:30]) + f", ... (+{count - 30} more)"
        lines.append(f"Completed Quests ({count}): {quest_list}")

    # Quests in progress
    in_progress = ctx.get("quests_in_progress")
    if in_progress and isinstance(in_progress, list):
        lines.append(f"In-Progress Quests ({len(in_progress)}): {', '.join(in_progress)}")

    # Achievement diaries — compact format
    diaries = ctx.get("diaries")
    if diaries and isinstance(diaries, dict):
        diary_parts = []
        for region, tiers in diaries.items():
            if not isinstance(tiers, dict):
                continue
            done_tiers = [t.capitalize() for t in ("easy", "medium", "hard", "elite") if tiers.get(t)]
            if done_tiers:
                diary_parts.append(f"{region.capitalize()} ({'/'.join(done_tiers)})")
        if diary_parts:
            lines.append(f"Diaries: {', '.join(diary_parts)}")

    # Location
    loc = ctx.get("location")
    if loc and isinstance(loc, dict) and "x" in loc and "y" in loc:
        lines.append(f"Location: ({loc['x']}, {loc['y']}, plane {loc.get('plane', 0)})")

    return "\n".join(lines)


class LlmClient:
    """Anthropic Claude client for generating OSRS expert responses."""

    def __init__(self):
        self.client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    async def generate_response(
        self,
        question: str,
        context_chunks: list[dict],
        game_mode: str = "main",
        use_deep_model: bool = False,
        conversation_history: list[dict] | None = None,
        player_context: dict | None = None,
    ) -> tuple[str, str]:
        """
        Generate an answer using Claude, grounded in wiki context.

        Args:
            conversation_history: Optional list of previous messages
                [{"role": "user"/"assistant", "content": "..."}].
                Limited to the last 10 messages to avoid context overflow.
            player_context: Optional dict with live player data (skills, quests, etc.)

        Returns:
            Tuple of (answer_text, model_used)
        """
        model = MODEL_DEEP if use_deep_model else MODEL_QUICK
        user_message = self._build_user_message(question, context_chunks, game_mode, player_context)
        messages = self._build_messages(user_message, conversation_history)

        try:
            response = await self.client.messages.create(
                model=model,
                max_tokens=1024,
                system=SYSTEM_PROMPT,
                messages=messages,
            )

            if not response.content:
                raise ValueError("Claude returned empty response")
            answer = response.content[0].text
            return answer, model

        except anthropic.APIError as e:
            logger.error(f"Claude API error: {e}")
            raise

    async def generate_response_stream(
        self,
        question: str,
        context_chunks: list[dict],
        game_mode: str = "main",
        use_deep_model: bool = False,
        conversation_history: list[dict] | None = None,
        player_context: dict | None = None,
    ) -> AsyncGenerator[tuple[str, str], None]:
        """
        Stream an answer using Claude, yielding text chunks as they arrive.

        Args:
            conversation_history: Optional list of previous messages
                [{"role": "user"/"assistant", "content": "..."}].
                Limited to the last 10 messages to avoid context overflow.
            player_context: Optional dict with live player data (skills, quests, etc.)

        Yields:
            Tuples of (text_chunk, model_used)
        """
        model = MODEL_DEEP if use_deep_model else MODEL_QUICK
        user_message = self._build_user_message(question, context_chunks, game_mode, player_context)
        messages = self._build_messages(user_message, conversation_history)

        try:
            async with self.client.messages.stream(
                model=model,
                max_tokens=1024,
                system=SYSTEM_PROMPT,
                messages=messages,
            ) as stream:
                async for text in stream.text_stream:
                    yield text, model

        except anthropic.APIError as e:
            logger.error(f"Claude streaming error: {e}")
            raise

    def _build_user_message(
        self,
        question: str,
        context_chunks: list[dict],
        game_mode: str,
        player_context: dict | None = None,
    ) -> str:
        """Build the full user message with player context, wiki context, and game mode."""
        context_text = self._build_context(context_chunks)

        # Auto-detect game mode from player context if available
        if player_context and "account_type" in player_context:
            detected = _account_type_to_game_mode(player_context["account_type"])
            if detected:
                game_mode = detected

        mode_context = GAME_MODE_CONTEXT.get(game_mode, GAME_MODE_CONTEXT["main"])

        parts = [
            f"Game Mode: {game_mode}",
            mode_context,
        ]

        # Inject player context between game mode and wiki context
        if player_context:
            player_text = _format_player_context(player_context)
            if player_text:
                parts.append("")
                parts.append("--- Player Context ---")
                parts.append(player_text)
                parts.append("--- End Player Context ---")

        parts.append("")
        parts.append("--- OSRS Wiki Context ---")
        parts.append(context_text)
        parts.append("--- End Context ---")
        parts.append("")
        parts.append(f"Player's Question: {question}")

        return "\n".join(parts)

    def _build_messages(
        self, current_user_message: str, conversation_history: list[dict] | None = None
    ) -> list[dict]:
        """
        Build the full messages list for the Claude API call.

        Prepends up to the last 10 conversation history messages before the
        current user message. This gives Claude multi-turn context while
        keeping the token budget reasonable.
        """
        messages: list[dict] = []

        if conversation_history:
            # Limit to last 10 messages to avoid context overflow
            recent_history = conversation_history[-10:]
            for msg in recent_history:
                messages.append({
                    "role": msg["role"],
                    "content": msg["content"],
                })

        # Always append the current user message (with wiki context) last
        messages.append({"role": "user", "content": current_user_message})
        return messages

    def _build_context(self, chunks: list[dict]) -> str:
        """Format retrieved chunks into context for the prompt."""
        if not chunks:
            return "No relevant wiki context found."

        parts = []
        for i, chunk in enumerate(chunks, 1):
            title = chunk.get("title", "Unknown")
            section = chunk.get("section_header", "")
            content = chunk.get("content", "")
            header = f"[Source {i}: {title}"
            if section:
                header += f" > {section}"
            header += "]"
            parts.append(f"{header}\n{content}")

        return "\n\n".join(parts)

    def should_use_deep_model(self, question: str) -> bool:
        """Decide whether a question needs the more powerful model."""
        complex_indicators = [
            "compare", "difference between", "best way", "optimal",
            "strategy", "should i", "worth it", "efficient",
            "how to", "guide", "explain", "why",
            "dps", "bis", "best in slot", "meta",
            "money making", "profit",
        ]
        q_lower = question.lower()
        return any(indicator in q_lower for indicator in complex_indicators)
