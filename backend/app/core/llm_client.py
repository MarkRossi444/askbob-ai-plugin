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
    ) -> tuple[str, str]:
        """
        Generate an answer using Claude, grounded in wiki context.

        Args:
            conversation_history: Optional list of previous messages
                [{"role": "user"/"assistant", "content": "..."}].
                Limited to the last 10 messages to avoid context overflow.

        Returns:
            Tuple of (answer_text, model_used)
        """
        model = MODEL_DEEP if use_deep_model else MODEL_QUICK
        user_message = self._build_user_message(question, context_chunks, game_mode)
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
    ) -> AsyncGenerator[tuple[str, str], None]:
        """
        Stream an answer using Claude, yielding text chunks as they arrive.

        Args:
            conversation_history: Optional list of previous messages
                [{"role": "user"/"assistant", "content": "..."}].
                Limited to the last 10 messages to avoid context overflow.

        Yields:
            Tuples of (text_chunk, model_used)
        """
        model = MODEL_DEEP if use_deep_model else MODEL_QUICK
        user_message = self._build_user_message(question, context_chunks, game_mode)
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
        self, question: str, context_chunks: list[dict], game_mode: str
    ) -> str:
        """Build the full user message with context and game mode."""
        context_text = self._build_context(context_chunks)
        mode_context = GAME_MODE_CONTEXT.get(game_mode, GAME_MODE_CONTEXT["main"])

        return f"""Game Mode: {game_mode}
{mode_context}

--- OSRS Wiki Context ---
{context_text}
--- End Context ---

Player's Question: {question}"""

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
