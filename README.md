# WiseOldMan.Ai

> Your in-game OSRS expert. An AI-powered RuneLite plugin that gives players instant, expert-level game knowledge backed by the entire OSRS wiki.

---

## What Is This?

WiseOldMan.Ai is a RuneLite side-panel plugin that provides an AI chatbot powered by the full Old School RuneScape wiki. Ask any question about OSRS — quests, skills, money-making, boss mechanics, item stats, drop tables — and get an accurate, contextual answer without leaving the game.

### Features
- **Full OSRS Wiki Knowledge** — Backed by 25,000+ scraped and indexed wiki pages
- **Game Mode Aware** — Tailored answers for main accounts, ironmen, UIM, HCIM, and GIM
- **Contextual Advice** — Not just wiki lookups; deep reasoning about strategy, optimization, and game mechanics
- **Always Current** — Automatically syncs with wiki updates
- **Seamless Integration** — Fits naturally into the RuneLite client with a futuristic AI-themed design

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Plugin | Java 11 + RuneLite API |
| Backend | Python + FastAPI |
| AI | Claude API (Anthropic) |
| Vector DB | PostgreSQL + pgvector (Supabase) |
| Scraping | Scrapy + BeautifulSoup4 |

---

## Project Structure

```
WiseOldMan.Ai/
├── plugin/          # RuneLite Java plugin
├── backend/         # Python FastAPI backend
├── scraper/         # OSRS Wiki scraping pipeline
└── docs/            # Project documentation
```

---

## Development

### Prerequisites
- Java 11 (JDK)
- Python 3.11+
- Gradle 7+
- Git

### Setup
```bash
# Clone the repository
git clone [repo-url]
cd WiseOldMan.Ai

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys

# Backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload

# Scraper
cd ../scraper
pip install -r requirements.txt
scrapy crawl osrs_wiki

# Plugin (requires RuneLite dev setup)
cd ../plugin
./gradlew build
```

---

## Status

**Phase**: Environment & Project Setup
**Version**: Pre-release (MVP in development)

See [docs/ROADMAP.md](docs/ROADMAP.md) for full development plan.

---

## License

TBD
