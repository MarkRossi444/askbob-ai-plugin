# Project Roadmap

> Current progress, active work, and planned phases. Updated by the Project Manager after every workflow execution.

---

## Current Status

**Active Phase**: Phase 1 — Environment & Project Setup
**Started**: 2026-02-12
**Progress**: 0%

---

## Phases Overview

```
[~] Phase 1: Environment & Project Setup    ░░░░░░░░░░░░ In Progress
[ ] Phase 2: OSRS Wiki Scraping Pipeline    ░░░░░░░░░░░░ Not Started
[ ] Phase 3: AI Backend Service             ░░░░░░░░░░░░ Not Started
[ ] Phase 4: RuneLite Plugin Development    ░░░░░░░░░░░░ Not Started
[ ] Phase 5: Integration & Testing          ░░░░░░░░░░░░ Not Started
[ ] Phase 6: Deployment & Launch            ░░░░░░░░░░░░ Not Started
```

---

## Phase 1: Environment & Project Setup

**Status**: In Progress
**Goal**: Dev environment fully configured, all project scaffolding in place, ready to build.

### Tasks
- [ ] Verify/install Java 11 (JDK), Python 3.11+, Gradle, Git
- [ ] Set up RuneLite plugin development environment
- [ ] Scaffold Python backend project (FastAPI)
- [ ] Scaffold Scrapy scraper project
- [ ] Set up Supabase project with pgvector
- [ ] Create .env.example with all required API key placeholders
- [ ] Initialize Git repository with .gitignore
- [ ] Verify full build chain works (Java plugin compiles, Python runs)

### Definition of Done
- [ ] All tools installed and verified
- [ ] Plugin compiles and loads in RuneLite dev mode
- [ ] Backend starts and serves a health endpoint
- [ ] Database connection works
- [ ] Git repo initialized with first commit

---

## Phase 2: OSRS Wiki Scraping Pipeline

**Status**: Not Started
**Goal**: Full wiki scraped, parsed, chunked, embedded, and stored in PostgreSQL+pgvector.

### Tasks
- [ ] Build Scrapy spider targeting oldschool.runescape.wiki
- [ ] Implement HTML parser to extract clean content from wiki pages
- [ ] Design content chunking strategy (by section, semantic boundaries)
- [ ] Implement embedding pipeline (Voyage AI / OpenAI)
- [ ] Design database schema (wiki_pages, wiki_embeddings)
- [ ] Build Scrapy pipeline to process and store data
- [ ] Run full wiki scrape
- [ ] Verify data quality and coverage
- [ ] Build incremental update mechanism (detect wiki changes)
- [ ] Set up scheduled update job (cron/scheduler)

### Definition of Done
- [ ] 100% of OSRS wiki pages scraped and stored
- [ ] Content properly chunked and embedded
- [ ] Semantic search returns relevant results for test queries
- [ ] Incremental updates detect and process wiki changes

---

## Phase 3: AI Backend Service

**Status**: Not Started
**Goal**: FastAPI service that receives questions and returns accurate, contextual answers using RAG.

### Tasks
- [ ] Set up FastAPI application structure
- [ ] Implement vector search (query embedding → pgvector similarity search)
- [ ] Build RAG pipeline (retrieve context → construct prompt → call Claude)
- [ ] Design system prompt for OSRS expert persona
- [ ] Implement game mode awareness in prompt construction
- [ ] Build chat API endpoint (POST /api/chat)
- [ ] Add rate limiting and input validation
- [ ] Add conversation context (multi-turn chat support)
- [ ] Performance testing and optimization

### Definition of Done
- [ ] API accepts questions and returns accurate answers
- [ ] Answers are grounded in wiki data (not hallucinated)
- [ ] Game mode context changes response appropriately
- [ ] Response time < 3 seconds
- [ ] Rate limiting works

---

## Phase 4: RuneLite Plugin Development

**Status**: Not Started
**Goal**: Polished RuneLite side panel plugin with chat UI and AI-themed design.

### Tasks
- [ ] Create RuneLite plugin skeleton (Plugin, Config, Panel classes)
- [ ] Build side panel UI with chat interface
- [ ] Implement message display (user messages + bot responses)
- [ ] Build API client to communicate with backend
- [ ] Add game mode selector
- [ ] Implement AI-themed visual design (glow effects, animations)
- [ ] Add loading states and error handling
- [ ] Add conversation history (scrollable)
- [ ] Plugin icon and branding
- [ ] Config panel (API settings, display preferences)

### Definition of Done
- [ ] Plugin loads in RuneLite and shows in side panel
- [ ] Users can type questions and receive answers
- [ ] UI matches design spec (dark theme + AI accents)
- [ ] All states handled (loading, error, empty)
- [ ] Game mode selector works

---

## Phase 5: Integration & Testing

**Status**: Not Started
**Goal**: All components working together, tested end-to-end, production-ready.

### Tasks
- [ ] End-to-end integration testing (plugin → API → RAG → response)
- [ ] Test with diverse OSRS questions (quests, skills, bosses, items, etc.)
- [ ] Test game mode-specific responses
- [ ] Performance optimization (caching, connection pooling)
- [ ] Security audit (API auth, input sanitization, rate limiting)
- [ ] Error handling and resilience testing
- [ ] Wiki update pipeline verification

### Definition of Done
- [ ] All integration tests pass
- [ ] 95%+ accuracy on test question set
- [ ] Performance targets met
- [ ] Security review passed

---

## Phase 6: Deployment & Launch

**Status**: Not Started
**Goal**: Backend deployed, plugin packaged, ready for public use.

### Tasks
- [ ] Deploy FastAPI backend to Railway/Render
- [ ] Configure production database on Supabase
- [ ] Set up monitoring and alerting
- [ ] Package plugin for RuneLite Plugin Hub submission
- [ ] Write user documentation / README
- [ ] Submit to RuneLite Plugin Hub
- [ ] Set up wiki update cron job in production

### Definition of Done
- [ ] Backend live and serving requests
- [ ] Plugin available on RuneLite Plugin Hub
- [ ] Monitoring active
- [ ] Wiki stays current automatically

---

## Blockers

| Blocker | Impact | Owner | Status |
|---------|--------|-------|--------|
| None yet | — | — | — |

---

## Backlog

Items for v2:
- [ ] Real-time game state integration (read player stats/inventory)
- [ ] Voice chat interface
- [ ] Mobile client support
- [ ] Player-specific recommendations from live account data
- [ ] Community Q&A feature (players can upvote best answers)
- [ ] Offline mode with cached common answers

---

## Recent Updates

| Date | Update |
|------|--------|
| 2026-02-12 | Project initialized — WiseOldMan.Ai |
