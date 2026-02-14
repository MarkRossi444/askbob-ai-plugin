# Agent Registry

> Master list of all active agents, their capabilities, and status for AskBob.Ai.

---

## Agent Roster

### Core Agents (Always Active)

| Agent | File | Status | Role |
|-------|------|--------|------|
| Setup Agent | `.claude/agents/core/setup.md` | ✅ Complete | First-run initialization (ran 2026-02-12) |
| Planner | `.claude/agents/core/planner.md` | ✅ Active | Strategic planning & approval |
| Orchestrator | `.claude/agents/core/orchestrator.md` | ✅ Active | Workflow design & model selection |
| Project Manager | `.claude/agents/core/project-manager.md` | ✅ Active | Task coordination & tracking |
| QA Engineer | `.claude/agents/core/qa-engineer.md` | ✅ Active | Validation & sign-off |
| Agent Builder | `.claude/agents/core/agent-builder.md` | ✅ Active | Dynamic agent creation |
| Documentation | `.claude/agents/core/documentation.md` | ✅ Active | Doc maintenance & session logging |

### Domain Agents (Activated for AskBob.Ai)

| Agent | File | Status | Activated For |
|-------|------|--------|---------------|
| Frontend Developer | `.claude/agents/domain/frontend-developer.md` | ✅ Active | RuneLite plugin UI (Java Swing), panel design |
| Backend Developer | `.claude/agents/domain/backend-developer.md` | ✅ Active | FastAPI service, database layer, business logic |
| UI/UX Designer | `.claude/agents/domain/ui-designer.md` | ✅ Active | Plugin panel design, AI-themed aesthetics |
| Brand Strategist | `.claude/agents/domain/brand-strategist.md` | ⬜ Inactive | — |
| Content Writer | `.claude/agents/domain/content-writer.md` | ⬜ Inactive | — |
| Data Engineer | `.claude/agents/domain/data-engineer.md` | ✅ Active | Wiki scraping pipeline, embedding, indexing |
| DevOps Engineer | `.claude/agents/domain/devops-engineer.md` | ✅ Active | Deployment, CI/CD, monitoring |
| Security Analyst | `.claude/agents/domain/security-analyst.md` | ✅ Active | API security, rate limiting, data protection |
| Mobile Developer | `.claude/agents/domain/mobile-developer.md` | ⬜ Inactive | — (v2 backlog) |
| API Architect | `.claude/agents/domain/api-architect.md` | ✅ Active | Plugin ↔ Backend API contract design |

### Generated Agents (Custom-Built for AskBob.Ai)

| Agent | File | Created | Purpose |
|-------|------|---------|---------|
| RuneLite Plugin Specialist | `.claude/agents/generated/runelite-plugin-specialist.md` | 2026-02-12 | RuneLite API expertise, plugin architecture, Java Swing UI for side panels |
| AI/RAG Engineer | `.claude/agents/generated/ai-rag-engineer.md` | 2026-02-12 | RAG pipeline design, prompt engineering, embedding strategy, vector search |

---

## Team Summary

- **Total Active**: 16 (7 core + 7 domain + 2 generated)
- **Project Type**: `custom`
- **Last Updated**: 2026-02-12

---

## Agent Capabilities Quick Reference

### Who Handles What?

| Task Type | Primary Agent | Support Agent |
|-----------|--------------|---------------|
| Strategic planning | Planner | — |
| Workflow design | Orchestrator | — |
| Task coordination | Project Manager | — |
| Quality validation | QA Engineer | — |
| New agent needs | Agent Builder | — |
| Documentation | Documentation Agent | All agents |
| RuneLite plugin code | RuneLite Plugin Specialist | Frontend Developer |
| Plugin panel UI design | UI/UX Designer | RuneLite Plugin Specialist |
| Backend API code | Backend Developer | API Architect |
| API contract design | API Architect | Backend Developer |
| Wiki scraping pipeline | Data Engineer | AI/RAG Engineer |
| RAG pipeline / prompts | AI/RAG Engineer | Backend Developer |
| Embedding strategy | AI/RAG Engineer | Data Engineer |
| Deployment / infra | DevOps Engineer | — |
| Security audit | Security Analyst | — |
