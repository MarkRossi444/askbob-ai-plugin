# Architectural Decision Records

> Log of significant decisions. Every agent records consequential decisions here with context and rationale.

---

## Decisions Log

### ADR-001: Project Initialization

**Date**: 2026-02-12
**Status**: Accepted
**Decided By**: Setup Agent + User

**Context**: Project needed to be classified and configured.

**Decision**: Classified as `custom` project type with 16 active agents (7 core + 7 domain + 2 generated).

**Rationale**: The project spans multiple domains (desktop plugin, backend API, data pipeline, AI/ML) and doesn't fit any single preset profile.

**Consequences**: Full agent team assembled with custom specialists for RuneLite and RAG.

---

### ADR-002: Tech Stack Selection

**Date**: 2026-02-12
**Status**: Accepted
**Decided By**: Setup Agent + User

**Context**: Needed to select technologies for a multi-component system: RuneLite plugin, backend API, scraping pipeline, AI integration, and data storage.

**Options Considered**:
1. **Python + FastAPI** for backend — Pros: Best AI/scraping ecosystem, async / Cons: Two languages (Java + Python)
2. **Java (Spring Boot)** for backend — Pros: Single language / Cons: Weaker AI/scraping libraries, more boilerplate
3. **Node.js** for backend — Pros: Fast dev / Cons: Weaker scraping ecosystem than Python

**Decision**: Python + FastAPI for backend/scraper. Java 11 for RuneLite plugin (required).

**Rationale**: Python has the strongest ecosystem for all three backend needs: web scraping (Scrapy), AI/LLM integration (LangChain, Anthropic SDK), and vector search. FastAPI provides async performance and auto-generated docs.

**Consequences**: Two-language project (Java + Python). Need both JDK and Python environments. Clean API boundary between plugin and backend.

---

### ADR-003: AI Model Selection — Claude API

**Date**: 2026-02-12
**Status**: Accepted
**Decided By**: Setup Agent + User

**Context**: Needed to select an LLM for powering the chatbot responses.

**Options Considered**:
1. **Claude API (Anthropic)** — Pros: Superior reasoning, excellent system prompts, great context window / Cons: Paid API
2. **OpenAI GPT-4** — Pros: Widely used, good ecosystem / Cons: Comparable cost, less control over persona
3. **Self-hosted (Llama, Mistral)** — Pros: Free / Cons: Worse quality, infrastructure burden, slower

**Decision**: Claude API with model tiering — Haiku for simple lookups, Sonnet for complex questions.

**Rationale**: Best reasoning capability for complex game advice. Excellent at following system prompts, which is critical for maintaining the OSRS expert persona. Model tiering keeps costs manageable.

**Consequences**: Ongoing API costs (usage-based). Need Anthropic API key. Can optimize costs by routing simple vs complex queries to appropriate model tier.

---

### ADR-004: Vector Database — PostgreSQL + pgvector via Supabase

**Date**: 2026-02-12
**Status**: Accepted
**Decided By**: Setup Agent + User

**Context**: Needed a vector database to store and search wiki embeddings.

**Options Considered**:
1. **PostgreSQL + pgvector (Supabase)** — Pros: Free tier, production-ready, UPSERT for updates, metadata filtering / Cons: Not a dedicated vector DB
2. **Pinecone** — Pros: Purpose-built for vectors / Cons: Paid, vendor lock-in
3. **ChromaDB** — Pros: Simple, free / Cons: Not production-ready, limited scaling
4. **Weaviate** — Pros: Full-featured / Cons: Complex setup, overkill for this scale

**Decision**: PostgreSQL + pgvector via Supabase free tier.

**Rationale**: Free to start, production-ready, handles 25K+ pages easily, supports metadata filtering (game mode, content type), UPSERT for incremental wiki updates. Same database can store application data if needed later.

**Consequences**: 500MB free tier limit (sufficient for MVP). Can migrate to dedicated vector DB later if needed.

---

### ADR-005: Plugin Name — WiseOldMan.Ai

**Date**: 2026-02-12
**Status**: Accepted
**Decided By**: User

**Context**: Needed a memorable, OSRS-relevant name for the plugin.

**Decision**: WiseOldMan.Ai

**Rationale**: References the iconic Wise Old Man NPC in Draynor Village — instantly recognizable to OSRS players. The ".Ai" suffix clearly communicates the AI-powered nature. Memorable, fun, and community-friendly.

**Consequences**: Brand identity established around this name. All assets and documentation use this name.
