# Technical Architecture

> Populated during setup and maintained as architectural decisions are made. The source of truth for how this project is built.

---

## Tech Stack

| Layer | Technology | Version | Rationale |
|-------|-----------|---------|-----------|
| RuneLite Plugin | Java 11 + RuneLite API | RuneLite latest | Required by RuneLite ecosystem. All plugins are Java. |
| Plugin Build | Gradle | 7.x+ | Standard RuneLite plugin build tool |
| Backend API | Python + FastAPI | Python 3.11+ / FastAPI 0.100+ | Best AI/ML/scraping ecosystem. Async, fast, auto-generates OpenAPI docs. |
| AI/LLM | Claude API (Anthropic) | Latest | Superior reasoning for complex game advice. Excellent system prompts. Haiku for quick lookups, Sonnet for complex questions. |
| Embeddings | Voyage AI or OpenAI text-embedding-3-small | Latest | High quality semantic search at low cost for converting wiki text to vectors. |
| Vector Database | PostgreSQL + pgvector (Supabase) | PG 15+ / pgvector 0.5+ | Free tier available. Production-ready. Handles 25K+ pages. Metadata filtering. UPSERT for incremental updates. |
| Web Scraping | Scrapy + BeautifulSoup4 | Latest | Scrapy for large-scale async crawling with rate limiting/retries. BS4 for HTML parsing. |
| Hosting (API) | Railway or Render | — | Free tiers to start. Easy Python deployment. Scales when needed. |
| Hosting (DB) | Supabase | Free tier | Managed PostgreSQL with pgvector support. 500MB free. |

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    OSRS Player (RuneLite)                     │
│  ┌───────────────────────────────────────────────────────┐  │
│  │           AskBob.Ai Side Panel Plugin              │  │
│  │  ┌─────────────┐  ┌──────────────────────────────┐   │  │
│  │  │  Chat Input  │  │  Chat Response Display       │   │  │
│  │  └──────┬──────┘  └──────────────▲───────────────┘   │  │
│  └─────────┼────────────────────────┼───────────────────┘  │
└────────────┼────────────────────────┼───────────────────────┘
             │ HTTPS POST             │ JSON Response
             ▼                        │
┌─────────────────────────────────────────────────────────────┐
│                   FastAPI Backend Service                     │
│  ┌──────────┐  ┌──────────────┐  ┌────────────────────┐    │
│  │  Router   │→│  RAG Pipeline │→│  Claude API Client  │    │
│  └──────────┘  └──────┬───────┘  └────────────────────┘    │
│                        │                                     │
│                        ▼                                     │
│               ┌────────────────┐                             │
│               │  Vector Search │                             │
│               │  (pgvector)    │                             │
│               └───────┬────────┘                             │
└───────────────────────┼─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│              PostgreSQL + pgvector (Supabase)                 │
│  ┌──────────────────┐  ┌─────────────────────────────────┐  │
│  │  wiki_pages       │  │  wiki_embeddings                │  │
│  │  (raw content)    │  │  (vector chunks + metadata)     │  │
│  └──────────────────┘  └─────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                        ▲
                        │ Scrape + Embed + Store
┌─────────────────────────────────────────────────────────────┐
│                 Wiki Scraping Pipeline                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌───────────┐  │
│  │  Scrapy   │→│  Parser   │→│  Chunker  │→│  Embedder  │  │
│  │  Spider   │  │  (BS4)    │  │           │  │ (Voyage/  │  │
│  └──────────┘  └──────────┘  └──────────┘  │  OpenAI)   │  │
│                                              └───────────┘  │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Scheduler (cron) — incremental updates               │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│              oldschool.runescape.wiki                         │
│              (25,000+ pages)                                  │
└─────────────────────────────────────────────────────────────┘
```

---

## Directory Structure

```
AskBob.Ai/
├── CLAUDE.md
├── README.md
├── .claude/
│   ├── agents/
│   │   ├── core/
│   │   ├── domain/
│   │   └── generated/
│   └── handoffs/
├── docs/
│   ├── PROJECT.md
│   ├── ARCHITECTURE.md
│   ├── BRAND.md
│   ├── ROADMAP.md
│   ├── WORKFLOWS.md
│   ├── DECISIONS.md
│   ├── SESSION-LOG.md
│   ├── AGENTS.md
│   ├── CHANGELOG.md
│   └── CONVENTIONS.md
├── plugin/                          # RuneLite Java plugin
│   ├── build.gradle
│   ├── settings.gradle
│   └── src/
│       └── main/
│           ├── java/
│           │   └── com/askbob/
│           │       ├── AskBobPlugin.java
│           │       ├── AskBobConfig.java
│           │       ├── AskBobPanel.java
│           │       └── api/
│           │           └── AskBobApiClient.java
│           └── resources/
│               └── com/askbob/
│                   └── icon.png
├── backend/                         # Python FastAPI backend
│   ├── pyproject.toml
│   ├── requirements.txt
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── api/
│   │   │   ├── routes/
│   │   │   │   └── chat.py
│   │   │   └── dependencies.py
│   │   ├── core/
│   │   │   ├── rag_pipeline.py
│   │   │   ├── llm_client.py
│   │   │   └── vector_search.py
│   │   ├── models/
│   │   │   ├── chat.py
│   │   │   └── wiki.py
│   │   └── services/
│   │       ├── chat_service.py
│   │       └── wiki_service.py
│   └── tests/
├── scraper/                         # OSRS Wiki scraping pipeline
│   ├── pyproject.toml
│   ├── requirements.txt
│   ├── scrapy.cfg
│   ├── osrs_scraper/
│   │   ├── spiders/
│   │   │   └── wiki_spider.py
│   │   ├── pipelines.py
│   │   ├── items.py
│   │   ├── settings.py
│   │   └── middlewares.py
│   ├── processing/
│   │   ├── parser.py
│   │   ├── chunker.py
│   │   └── embedder.py
│   └── scheduler/
│       └── update_scheduler.py
└── .env.example                     # Environment variable template
```

---

## Key Integrations

| Service | Purpose | Auth Method |
|---------|---------|-------------|
| Claude API (Anthropic) | LLM for chatbot responses | API Key |
| Voyage AI / OpenAI | Text embeddings for semantic search | API Key |
| Supabase | Managed PostgreSQL + pgvector | Connection string + API Key |
| OSRS Wiki | Source of all game knowledge | Public (respect rate limits) |
| RuneLite Plugin Hub | Plugin distribution | GitHub + Plugin Hub submission |

---

## Environments

| Environment | URL/Location | Purpose |
|------------|-------------|---------|
| Development | localhost:8000 (API), RuneLite dev mode (plugin) | Local development |
| Staging | TBD (Railway/Render preview) | Pre-production testing |
| Production | TBD (Railway/Render) | Live API serving plugin users |

---

## Security Considerations

- API keys stored in environment variables only, never committed to git
- Rate limiting on backend API to prevent abuse
- Input sanitization on all user queries
- No storage of player credentials or sensitive account data
- HTTPS only for all API communication
- Wiki scraping respects robots.txt and rate limits

---

## Performance Requirements

| Metric | Target |
|--------|--------|
| Chat response time | < 3 seconds end-to-end |
| Vector search latency | < 500ms |
| Wiki scrape throughput | Full scrape in < 4 hours |
| Incremental update | < 30 minutes for daily changes |
| Concurrent users | 100+ simultaneous (MVP target) |

---

## Document History

| Date | Change | Author |
|------|--------|--------|
| 2026-02-12 | Initial architecture | Setup Agent |
