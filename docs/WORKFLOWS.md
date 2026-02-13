# Workflows

> Agent sequences for WiseOldMan.Ai. Configured during setup based on active agent team.

---

## Universal Execution Prefix (ALL Workflows)

```
Planner → [User Approval] → Orchestrator → [Implementation] → QA
```

This prefix is mandatory. No workflow bypasses it.

---

## Active Workflows

### Standard Feature Build
```
PM → [Domain Specialists in dependency order] → QA
```
Used for: New features, major additions.

### Wiki Scraping Pipeline Build
```
PM → Data Engineer → AI/RAG Engineer → Backend Developer → QA
```
Used for: Scraping spider, parsing, chunking, embedding pipeline.

### AI Backend Development
```
PM → API Architect → AI/RAG Engineer → Backend Developer → Security Analyst → QA
```
Used for: RAG pipeline, API endpoints, Claude integration.

### RuneLite Plugin Development
```
PM → RuneLite Plugin Specialist → UI/UX Designer → Frontend Developer → QA
```
Used for: Plugin UI, side panel, Java client code.
Note: Frontend Developer handles Java UI code in this context.

### Full Stack Feature (Plugin + Backend)
```
PM → API Architect (contract) → [Backend Developer + RuneLite Plugin Specialist (parallel)] → QA
```
Used for: Features that require changes to both plugin and backend.

### Design Update
```
UI/UX Designer → Frontend Developer / RuneLite Plugin Specialist → QA
```
Used for: Visual changes, layout updates, animation work.

### Bug Fix
```
QA (diagnose) → [Relevant Developer] (fix) → QA (verify)
```
Used for: Bug reports, regressions.

### Security Review
```
Security Analyst → [Relevant Developer] (fix) → Security Analyst (verify) → QA
```
Used for: Security audits, vulnerability fixes.

### Documentation Update
```
Documentation Agent → QA
```
Used for: Doc updates, session logging.

---

## Workflow Selection Guide

| Task | Workflow | Notes |
|------|---------|-------|
| New scraping feature | Wiki Scraping Pipeline Build | Data Engineer leads |
| New API endpoint | AI Backend Development | API Architect designs first |
| Plugin UI change | RuneLite Plugin Development | Plugin Specialist leads |
| Full feature (both sides) | Full Stack Feature | API contract first, then parallel |
| Visual/design change | Design Update | Designer specs first |
| Bug fix | Bug Fix | QA diagnoses first |
| Security concern | Security Review | Security Analyst leads |
| Doc update | Documentation Update | Minimal workflow |

---

## Parallel Execution Rules

### Can Run in Parallel
- Backend and plugin development (after API contract agreed)
- Independent bug fixes in unrelated components
- Documentation updates alongside any work
- Scraper updates alongside backend/plugin work

### Cannot Run in Parallel
- API contract must be agreed before parallel backend/plugin work
- Database schema changes must complete before dependent code
- Security fixes must complete before deployment

---

## Document History

| Date | Change | Author |
|------|--------|--------|
| 2026-02-12 | Initial workflows configured for WiseOldMan.Ai | Setup Agent |
