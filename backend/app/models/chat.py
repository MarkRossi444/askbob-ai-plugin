"""Request and response models for the chat API."""

from pydantic import BaseModel, Field


class Message(BaseModel):
    """A single message in a conversation (user or assistant)."""
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str = Field(..., min_length=1, max_length=500)


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    game_mode: str = Field(default="main")
    conversation_id: str | None = None
    messages: list[Message] = Field(
        default_factory=list,
        max_length=20,
        description="Previous conversation messages for multi-turn context",
    )
    player_context: dict | None = Field(
        default=None,
        description="Live player data: skills, quests, account type, location, diaries",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "question": "What are the requirements for Dragon Slayer II?",
                "game_mode": "main",
                "messages": [
                    {"role": "user", "content": "Tell me about Dragon Slayer II"},
                    {"role": "assistant", "content": "Dragon Slayer II is a grandmaster quest..."},
                ],
                "player_context": {
                    "account_type": "IRONMAN",
                    "combat_level": 95,
                    "total_level": 1456,
                    "skills": {"attack": {"level": 75, "xp": 1210421}},
                    "quests_completed": ["Dragon Slayer I"],
                    "quests_in_progress": ["Song of the Elves"],
                },
            }
        }


class Source(BaseModel):
    title: str
    section: str
    url: str
    similarity: float


class ChatResponse(BaseModel):
    answer: str
    sources: list[Source] = []
    game_mode: str
    model: str
