# Project Definition

> Populated by the Setup Agent during initialization. This is the single source of truth for what this project is, why it exists, and what success looks like.

---

## Identity

**Project Name**: `AskBob.Ai`
**One-Line Description**: An AI-powered RuneLite plugin that gives OSRS players instant, expert-level game knowledge via an in-game chatbot backed by the full OSRS wiki.
**Project Type**: `custom`

---

## The Problem

OSRS players constantly alt-tab out of the game to search the wiki for quest guides, money-making methods, item stats, drop tables, skill training paths, and game mechanics. This breaks immersion, wastes time, and is especially painful for ironman/UIM accounts that need highly specific, mode-aware advice. There is no in-game tool that provides dynamic, contextual, expert-level answers.

---

## The Solution

AskBob.Ai is a RuneLite side-panel plugin that provides an AI chatbot powered by the entire OSRS wiki knowledge base. Players type questions in natural language and receive accurate, contextual answers without leaving the game. The AI understands game modes (main, ironman, UIM, HCIM, GIM), can provide quest walkthroughs, optimal training paths, money-making strategies, boss mechanics, and any other information found on the wiki — all delivered conversationally and tailored to the player's context.

---

## Target Audience

### Primary
- **Who**: All OSRS players using the RuneLite client
- **Needs**: Quick, accurate game information without leaving the client
- **Pain Points**: Constant alt-tabbing to wiki, information overload on wiki pages, no game-mode-specific filtering, no conversational interface for complex questions

### Secondary
- **Who**: New OSRS players and returning players
- **Needs**: Guided advice, "what should I do next" type help, understanding of game mechanics
- **Pain Points**: Overwhelming amount of content, don't know what to search for, need contextual rather than encyclopedic answers

---

## Goals & Success Metrics

### Primary Goal
Players can ask any OSRS question and receive an accurate, contextual answer directly in the RuneLite client.

### Secondary Goals
- Full OSRS wiki scraped, indexed, and searchable via semantic search
- Wiki data stays automatically current with game updates
- Game mode awareness for tailored advice

### Success Metrics
| Metric | Target | Measurement |
|--------|--------|-------------|
| Answer accuracy | 95%+ correct answers for wiki-answerable questions | Manual QA testing against known questions |
| Response time | < 3 seconds per answer | API latency monitoring |
| Wiki coverage | 100% of OSRS wiki pages scraped and indexed | Scraper completion metrics |
| Plugin installs | Growth in RuneLite Plugin Hub downloads | Plugin Hub analytics |

---

## Scope

### In Scope (MVP)
- Full OSRS wiki scraping pipeline with incremental updates
- Vector embedding and semantic search over wiki content
- AI chatbot backend (Claude API + RAG pipeline)
- RuneLite side panel plugin with chat UI
- Game mode awareness (main, ironman, UIM, HCIM, GIM)
- Futuristic AI-themed panel design with glow/animation effects

### Out of Scope (v2 — Deferred)
- Real-time game state integration (reading player stats/inventory)
- Voice chat interface
- Mobile client support
- Player-specific recommendations based on live account data

### Explicit Non-Goals
- Botting or automation — this is strictly an information tool
- Replacing the wiki — this is a complementary interface

---

## Constraints

- **Timeline**: No hard deadline — fast but built well
- **Budget**: Open — flag any paid services before use
- **Technical**: Must be a valid RuneLite plugin (Java 11, Gradle, RuneLite API). Backend must be performant enough for real-time chat.
- **Other**: Must respect OSRS wiki's terms of service for scraping. Must not violate Jagex's ToS or RuneLite's plugin guidelines.

---

## Exit Strategy

Scale and maintain — build as a free community plugin, grow the user base through RuneLite Plugin Hub, and maintain as a long-term open-source project.

---

## Document History

| Date | Change | Author |
|------|--------|--------|
| 2026-02-12 | Initial project definition | Setup Agent |
