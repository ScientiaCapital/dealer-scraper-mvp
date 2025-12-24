# BACKLOG.md - Project Task Board

**Project**: Dealer Scraper MVP - OEM Dealer Intelligence Platform
**Last Updated**: 2025-12-24
**Sprint**: Current

---

## Quick Stats

| Status | Count |
|--------|-------|
| 🔴 Blocked | 0 |
| 🟡 In Progress | 0 |
| 🟢 Ready | 2 |
| ✅ Done (this sprint) | 4 |

---

## 📋 Board View

### 🔴 Blocked
*None currently*

---

### 🟡 In Progress
*None currently*

---

### 🟢 Ready (Prioritized)

#### 1. [HIGH] Close CRM Custom Fields Implementation
- **ID**: TASK-001
- **Assignee**: Unassigned
- **Labels**: `feature`, `crm`, `integration`
- **Est. Time**: 4-6 hours
- **Dependencies**: None

**⚠️ PROJECT BOUNDARY NOTE**: This task will be MOVED to sales-agent repo for production deployment. dealer-scraper should only push to Supabase per project architecture.

**Description**: Create OEM Certifications and State Licenses multi-value fields in Close CRM, create OEM Count number field, implement sync script, test with 5 leads, and create Smart Views for OEM filtering.

**Acceptance Criteria**:
- [ ] OEM Certifications multi-value field created in Close CRM
- [ ] State Licenses multi-value field created in Close CRM
- [ ] OEM Count number field created
- [x] `scripts/sync_to_close_crm.py` implemented (COMPLETE - 29 TDD tests)
- [ ] Tested with 5 leads (Tim Kipper as owner) - READY for testing
- [ ] Smart Views created for OEM filtering
- [x] All tests pass (29/29 sync tests passing)
- [ ] `/validate` passes

---

#### 2. [MEDIUM] Trane Detail Page Enrichment
- **ID**: TASK-002
- **Assignee**: Unassigned
- **Labels**: `feature`, `scraping`, `enrichment`
- **Est. Time**: 1 day
- **Dependencies**: None

**Description**: Fix 2,802 Trane records with 0% contact info by scraping detail pages for Google ratings, review count, certifications/tier, and business hours. Detail pages have PRE-QUALIFICATION data verified by Trane.

**Acceptance Criteria**:
- [ ] Detail page scraper implemented for Trane
- [ ] Google ratings extracted
- [ ] Review count captured
- [ ] Certifications/tier data extracted
- [ ] Business hours captured
- [ ] 2,802 Trane records enriched
- [ ] All tests pass
- [ ] `/validate` passes

---

### ⏸️ Backlog (Future)

| ID | Title | Priority | Labels |
|----|-------|----------|--------|
| TASK-003 | Fix Broken Scrapers (16 OEMs) | High | `bug`, `scraping` |
| TASK-004 | Implement Rate Limiting | Medium | `feature`, `performance` |

---

### ✅ Done (This Sprint)

| ID | Title | Completed | By |
|----|-------|-----------|-----|
| TASK-000 | Context Engineering Setup | 2025-11-30 | Claude |
| TASK-005 | Browserbase Retry Logic | 2025-12-24 | Claude |
| TASK-006 | Colorado DORA Migration | 2025-12-24 | Claude |
| TASK-007 | Close CRM Sync Script | 2025-12-24 | Claude |

---

## 🔄 Workflow

### Task Lifecycle
```
Ready → In Progress → Review → Done
         ↓
       Blocked (if dependencies)
```

### How to Use This File

**Starting a task**:
1. Move task from "Ready" to "In Progress"
2. Add your name as Assignee
3. Update the date

**Completing a task**:
1. Check all acceptance criteria boxes
2. Move to "Done" section
3. Add completion date

**Adding a new task**:
1. Add to "Backlog" table first
2. When prioritized, create full entry in "Ready"
3. Include: ID, description, acceptance criteria

---

## 🔗 Related Files

| File | Purpose |
|------|---------|
| `CLAUDE.md` | Project overview and rules |
| `PLANNING.md` | Architecture decisions |
| `TASK.md` | Quick task reference |
| `PRPs/` | Implementation plans |
| `/validate` | Run before completing tasks |

---

## Critical Rules Reminder

- **NO OpenAI** - Use DeepSeek, Qwen, Moonshot via OpenRouter
- **API keys in .env only** - Never hardcode
- **ALWAYS create failsafe archive before database changes**
- **Run `/validate` before marking tasks done**
- **Update this file as work progresses**

---

*This file is the source of truth for sprint tasks. Keep it updated!*
