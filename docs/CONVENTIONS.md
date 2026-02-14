# Project Conventions

> Naming, coding, and style standards for AskBob.Ai.

---

## Naming Conventions

| Context | Convention | Example |
|---------|-----------|---------|
| Java Classes | PascalCase | `AskBobPlugin`, `AskBobPanel` |
| Java Methods/Variables | camelCase | `sendChatMessage`, `userQuery` |
| Java Constants | SCREAMING_SNAKE_CASE | `MAX_MESSAGE_LENGTH`, `API_BASE_URL` |
| Java Packages | lowercase dot-separated | `com.askbob.api` |
| Python Modules | snake_case | `rag_pipeline.py`, `wiki_spider.py` |
| Python Functions/Variables | snake_case | `get_wiki_content`, `query_embedding` |
| Python Classes | PascalCase | `ChatService`, `WikiSpider` |
| Python Constants | SCREAMING_SNAKE_CASE | `EMBEDDING_DIMENSION`, `CHUNK_SIZE` |
| API Endpoints | kebab-case | `/api/chat`, `/api/health` |
| Database Tables | snake_case | `wiki_pages`, `wiki_embeddings` |
| Database Columns | snake_case | `page_title`, `last_scraped_at` |
| CSS/Design Tokens | kebab-case | `--color-ai-accent` |
| Files (general) | kebab-case | `chat-service.py`, `wiki-spider.py` |
| Agent Files | kebab-case.md | `runelite-plugin-specialist.md` |
| Config/Env | SCREAMING_SNAKE_CASE | `ANTHROPIC_API_KEY`, `DATABASE_URL` |

---

## Git Conventions

### Commit Format
```
type(scope): description

[optional body]
```

### Types
`feat` | `fix` | `docs` | `style` | `refactor` | `test` | `chore` | `build` | `ci`

### Scopes
`plugin` | `backend` | `scraper` | `db` | `api` | `docs` | `infra`

### Examples
```
feat(scraper): add wiki spider with full-site crawling
fix(backend): handle empty embedding results in vector search
docs(readme): add setup instructions for local development
feat(plugin): implement chat panel with message history
```

### Branch Naming
```
feature/[short-description]
fix/[issue-description]
docs/[what-changed]
```

---

## Code Standards

### Java (RuneLite Plugin)
- Java 11 syntax (no newer features)
- Follow RuneLite plugin conventions and patterns
- Use RuneLite's `@Inject` for dependency injection
- Use `@Subscribe` for event handling
- Panel extends `PluginPanel`
- Config uses RuneLite `@ConfigGroup` / `@ConfigItem` annotations
- No hardcoded strings — use constants or config
- All API calls on background threads (not EDT)

### Python (Backend + Scraper)
- Python 3.11+ with type hints on all function signatures
- FastAPI async endpoints where applicable
- Pydantic models for request/response validation
- Environment variables via `python-dotenv` or Pydantic Settings
- Async database operations where possible
- Scrapy conventions for spider implementation
- f-strings for string formatting (not .format() or %)

---

## File Organization

### Plugin (Java)
```
plugin/src/main/java/com/askbob/
├── AskBobPlugin.java      # Main plugin class
├── AskBobConfig.java      # Config interface
├── AskBobPanel.java       # Side panel UI
└── api/
    └── AskBobApiClient.java  # Backend API client
```

### Backend (Python)
```
backend/app/
├── main.py                    # FastAPI app entry point
├── config.py                  # Settings and configuration
├── api/routes/                # API endpoint handlers
├── core/                      # Core business logic (RAG, LLM, vector search)
├── models/                    # Pydantic data models
└── services/                  # Service layer
```

### Scraper (Python)
```
scraper/osrs_scraper/
├── spiders/                   # Scrapy spiders
├── pipelines.py               # Data processing pipelines
├── items.py                   # Scrapy item definitions
└── settings.py                # Scrapy configuration
```

---

## Document History

| Date | Change | Author |
|------|--------|--------|
| 2026-02-12 | Initial conventions for AskBob.Ai | Setup Agent |
