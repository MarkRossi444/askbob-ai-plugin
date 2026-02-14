# CLAUDE.md — Universal Project Seed v1.0

> Master instruction set for Claude Code multi-agent system. This is the canonical source for all project behavior, standards, and agent coordination. Every agent reads this file first.

---

## System State

**Project Name**: `AskBob.Ai`
**Project Type**: `custom`
**Initialized**: `true`
**Setup Date**: `2026-02-12`

---

## How This System Works

This is a **self-configuring multi-agent framework**. It operates in two modes:

### Mode 1: SETUP (First Run)
When `INITIALIZED` is `false`, the system runs an interactive setup sequence that interviews the user, understands the project, populates all documentation, and dynamically generates the specialized agents needed for this specific project.

### Mode 2: EXECUTION (All Subsequent Work)
Once initialized, every task follows the mandatory execution pipeline below.

---

## Mandatory Execution Pipeline

```
┌─────────────────────────────────────────────────────────────┐
│  GATE 1: SESSION START                                      │
│  → Read CLAUDE.md, docs/ROADMAP.md, check git history       │
│  → Restore context from docs/SESSION-LOG.md                 │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────┐
│  GATE 2: PLANNER AGENT (Always First)                       │
│  → Deep analysis of user request                            │
│  → Strategic execution plan with phases, agents, risks      │
│  → Presents plan and WAITS for explicit user approval       │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────┐
│  GATE 3: USER APPROVAL (Hard Gate — Cannot Be Bypassed)     │
│  → User must say "approved" or request changes              │
│  → If changes requested → Planner revises → re-submit       │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────┐
│  GATE 4: ORCHESTRATOR AGENT                                 │
│  → Translates plan into optimized AI execution map          │
│  → Selects Claude model per agent (Opus/Sonnet/Haiku)       │
│  → Identifies parallel vs sequential execution              │
│  → Produces detailed execution map with dependencies        │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────┐
│  GATE 5: IMPLEMENTATION                                     │
│  → Agents execute per the orchestrator's map                │
│  → Each agent follows handoff protocol                      │
│  → Progress tracked in docs/SESSION-LOG.md                  │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────┐
│  GATE 6: QA & VALIDATION                                    │
│  → QA agent validates all outputs                           │
│  → Sign-off or bug reports generated                        │
│  → docs/ROADMAP.md and docs/SESSION-LOG.md updated          │
└─────────────────────────────────────────────────────────────┘
```

### Rules — No Exceptions

1. **Never skip the Planner.** Every task starts with planning.
2. **Never execute without approval.** The user must explicitly approve.
3. **Never begin implementation before the Orchestrator completes.**
4. **Never skip QA.** Every deliverable gets validated.
5. **Always update docs.** SESSION-LOG, ROADMAP, and DECISIONS stay current.
6. **Always use handoff protocols.** No informal agent transitions.

---

## Agent System

Agents are organized into three tiers:

### Tier 1 — Core Agents (Always Present, Every Project)

These agents exist in every project regardless of type. They form the execution backbone.

| Agent | File | Role | Removable? |
|-------|------|------|------------|
| **Setup Agent** | `.claude/agents/core/setup.md` | First-run initialization & user interview | No |
| **Planner** | `.claude/agents/core/planner.md` | Strategic analysis & execution planning | No |
| **Orchestrator** | `.claude/agents/core/orchestrator.md` | AI workflow design & model selection | No |
| **Project Manager** | `.claude/agents/core/project-manager.md` | Task coordination & progress tracking | No |
| **QA Engineer** | `.claude/agents/core/qa-engineer.md` | Universal validation & sign-off | No |
| **Agent Builder** | `.claude/agents/core/agent-builder.md` | Dynamic agent creation & configuration | No |
| **Documentation Agent** | `.claude/agents/core/documentation.md` | Keeps all project docs current | No |

### Tier 2 — Domain Agents (Pre-Built Specialists)

Pre-built agents for common project types. The Setup Agent and Agent Builder select which ones to activate based on project type.

| Agent | File | Domain |
|-------|------|--------|
| Frontend Developer | `.claude/agents/domain/frontend-developer.md` | Web/App Development |
| Backend Developer | `.claude/agents/domain/backend-developer.md` | API/Server Development |
| UI/UX Designer | `.claude/agents/domain/ui-designer.md` | Visual Design |
| Brand Strategist | `.claude/agents/domain/brand-strategist.md` | Brand & Messaging |
| Content Writer | `.claude/agents/domain/content-writer.md` | Copy & Documentation |
| Data Engineer | `.claude/agents/domain/data-engineer.md` | Data Pipelines & Analytics |
| DevOps Engineer | `.claude/agents/domain/devops-engineer.md` | Infrastructure & CI/CD |
| Security Analyst | `.claude/agents/domain/security-analyst.md` | Security Auditing |
| Mobile Developer | `.claude/agents/domain/mobile-developer.md` | iOS/Android/React Native |
| API Architect | `.claude/agents/domain/api-architect.md` | API Design & Integration |

### Tier 3 — Generated Agents (Custom-Built Per Project)

Created by the Agent Builder when a project needs capabilities not covered by Core or Domain agents. Stored in `.claude/agents/generated/` with full documentation.

---

## Project Type Profiles

The Setup Agent uses these profiles to determine which Domain agents to activate and what documentation structure to create.

| Profile | Domain Agents Activated | Use Cases |
|---------|------------------------|-----------|
| `web-app` | Frontend, Backend, UI/UX, Brand, Content | SaaS, web platforms, dashboards |
| `mobile-app` | Mobile, Backend, UI/UX, Brand, Content | iOS, Android, React Native apps |
| `full-stack` | Frontend, Backend, Mobile, UI/UX, API, DevOps | Full product builds |
| `design-system` | UI/UX, Frontend, Brand, Content | Component libraries, themes |
| `api-service` | Backend, API, DevOps, Security | Microservices, APIs |
| `data-pipeline` | Data, Backend, DevOps | ETL, analytics, ML pipelines |
| `automation` | Backend, DevOps, API | Workflow automation, integrations |
| `marketing-site` | Frontend, UI/UX, Brand, Content | Landing pages, marketing |
| `shopify-theme` | Frontend, UI/UX, Brand, Content | Shopify theme development |
| `custom` | Agent Builder creates bespoke team | Anything else |

---

## Documentation System

All project knowledge lives in `/docs`. Documents are populated during setup and maintained throughout the project lifecycle.

| Document | Purpose | Updated By |
|----------|---------|------------|
| `docs/PROJECT.md` | Project definition, goals, scope, audience | Setup Agent |
| `docs/ARCHITECTURE.md` | Technical architecture & stack decisions | Planner / Domain Agents |
| `docs/BRAND.md` | Brand identity, voice, visual standards | Brand Strategist |
| `docs/ROADMAP.md` | Phases, progress, active work | Project Manager |
| `docs/WORKFLOWS.md` | Agent sequences for this project | Orchestrator |
| `docs/DECISIONS.md` | Architectural decision records | All agents |
| `docs/SESSION-LOG.md` | Cross-session continuity & state | Documentation Agent |
| `docs/AGENTS.md` | Registry of all active agents & capabilities | Agent Builder |
| `docs/CHANGELOG.md` | Chronological record of changes | Documentation Agent |
| `docs/CONVENTIONS.md` | Naming, coding, and style conventions | Setup Agent / Domain Agents |

---

## Workflow Patterns

### Universal Prefix (Required for ALL Workflows)
```
Planner → [User Approval] → Orchestrator → [Implementation Agents] → QA
```

### Dynamic Workflow Selection
The Orchestrator selects the optimal workflow based on task type. Common patterns:

| Task Type | Pattern |
|-----------|---------|
| New Feature | PM → [Domain Specialists in dependency order] → QA |
| Bug Fix | QA (diagnose) → Developer (fix) → QA (verify) |
| Refactor | PM (scope) → Developer (refactor) → QA (regression) |
| Content Update | Brand → Content → QA |
| Design Update | UI/UX → Developer → QA |
| New Integration | API Architect → Developer → Security → QA |
| Infrastructure | DevOps → Security → QA |
| Documentation | Documentation Agent → QA |

---

## Operating Principles

### 1. Plan Before Building
Every task starts with the Planner Agent. No exceptions. Read relevant documentation before starting work.

### 2. Structured Handoffs
Use formal handoff protocols from `.claude/handoffs/`. Every agent specifies inputs, outputs, and completion criteria.

### 3. Documentation Is Not Optional
Update documentation BEFORE or ALONGSIDE implementation. Record decisions in `docs/DECISIONS.md`. Keep `docs/ROADMAP.md` current.

### 4. Quality Over Speed
Clean, readable code over clever code. Follow existing patterns. No hardcoded values. Accessibility by default.

### 5. Git Discipline
Commit frequently with conventional commits: `type(scope): description`
Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`, `build`, `ci`

### 6. Security By Default
Never store secrets in code or docs. Use environment variables. Never commit `.env` files. Validate all inputs.

---

## Session Protocol

Every new session follows this sequence:

1. Read `CLAUDE.md` (this file)
2. Read `docs/SESSION-LOG.md` for continuity
3. Read `docs/ROADMAP.md` for current state
4. Check recent git history
5. **If `INITIALIZED` is `false`**: Run Setup Agent
6. **If `INITIALIZED` is `true`**: Start with Planner Agent for the user's request

---

## Directory Structure

```
project-root/
├── CLAUDE.md                          # This file — master instructions
├── README.md                          # Project README (generated during setup)
├── .claude/
│   ├── agents/
│   │   ├── core/                      # Permanent agents (never removed)
│   │   │   ├── setup.md
│   │   │   ├── planner.md
│   │   │   ├── orchestrator.md
│   │   │   ├── project-manager.md
│   │   │   ├── qa-engineer.md
│   │   │   ├── agent-builder.md
│   │   │   └── documentation.md
│   │   ├── domain/                    # Pre-built specialist agents
│   │   │   ├── frontend-developer.md
│   │   │   ├── backend-developer.md
│   │   │   ├── ui-designer.md
│   │   │   ├── brand-strategist.md
│   │   │   ├── content-writer.md
│   │   │   ├── data-engineer.md
│   │   │   ├── devops-engineer.md
│   │   │   ├── security-analyst.md
│   │   │   ├── mobile-developer.md
│   │   │   └── api-architect.md
│   │   ├── generated/                 # Custom agents built per project
│   │   │   └── (created by Agent Builder)
│   │   └── _template.md              # Template for creating new agents
│   └── handoffs/
│       └── handoff-template.md
├── docs/
│   ├── PROJECT.md                     # Project definition
│   ├── ARCHITECTURE.md                # Technical architecture
│   ├── BRAND.md                       # Brand guidelines
│   ├── ROADMAP.md                     # Progress tracking
│   ├── WORKFLOWS.md                   # Agent workflows
│   ├── DECISIONS.md                   # Decision records
│   ├── SESSION-LOG.md                 # Cross-session state
│   ├── AGENTS.md                      # Active agent registry
│   ├── CHANGELOG.md                   # Change history
│   └── CONVENTIONS.md                 # Project conventions
└── [project source files]
```

---

## Configuration

### Naming Conventions (Defaults — Override in docs/CONVENTIONS.md)
- Components: `PascalCase`
- Functions/Variables: `camelCase`
- Constants: `SCREAMING_SNAKE_CASE`
- Files: `kebab-case`
- CSS/Tokens: `kebab-case`
- Agents: `kebab-case.md`

### Model Selection Defaults
| Complexity | Model | Use For |
|------------|-------|---------|
| High | Opus | Strategy, architecture, creative, complex reasoning |
| Medium | Sonnet | Implementation, standard code, moderate complexity |
| Low | Haiku | Simple edits, file ops, quick checks, formatting |
