# 🚀 UNIVERSAL PROJECT WORKFLOW v2.0
**Core Principle:** Every skill, every gate, maximum parallelization

---

## 🌅 START DAY (Enhanced)
Load: workflow-enforcer + project-context-skill + planning-prompts

```bash
// CONTEXT SCAN (30 seconds)
1. pwd → Detect project
2. Load PROJECT_CONTEXT.md → Verify against git state
3. Check: recent commits, uncommitted changes, active worktrees
4. Scan: CLAUDE.md, PLANNING.md, TASK.md, Backlog.md

// WORKTREE STATUS (new)
5. cat ~/.claude/worktree-registry.json | jq '[.[] | select(.project == "'$(basename $PWD)'")] | length'
   → Report: "X active worktrees for this project"

// COST STATUS (new - from lang-core patterns)
6. If cost tracking exists:
   → Today's spend, MTD spend, cost-per-task average
   → Alert if approaching budget thresholds

// OUTPUT FORMAT
Summarize:
├── ✅ Completed (last session): [list]
├── 🔄 In Progress: [task] → [worktree/branch]
├── 🚫 Blockers: [issues needing resolution]
├── 📋 Priority Queue:
│   1. [task] → Agent: [specific agent] → Parallel: [yes/no]
│   2. [task] → Agent: [specific agent] → Parallel: [yes/no]
│   3. [task] → Agent: [specific agent] → Parallel: [yes/no]
└── 💰 Cost Context: [spend summary if tracked]
```

---

## 🔬 RESEARCH PHASE (NEW - Before Implementation)
Load: research-skill + planning-prompts

```bash
// TRIGGER: Before ANY feature development
// PURPOSE: Don't build blind

1. SCAN existing solutions:
   - Check mcp-server-cookbook: /Users/tmkipper/Desktop/tk_projects/mcp-server-cookbook/
   - Web search for prior art, patterns, pitfalls
   - Check your 70+ repos for reusable code

2. EVALUATE approach:
   - Framework selection → Use research-skill evaluation checklist
   - LLM selection → Default Chinese LLMs (DeepSeek V3 for bulk, Claude Sonnet for reasoning)
   - Infrastructure → Supabase/Neon/RunPod based on needs

3. COST PROJECTION:
   - Estimate inference costs (use ai-cost-optimizer patterns)
   - Estimate compute costs
   - Flag if project exceeds $X threshold

4. OUTPUT: RESEARCH.md → FINDINGS.md (per planning-prompts hierarchy)
   - Substantive one-liner summary
   - Confidence score, dependencies, open questions
   - Go/No-Go recommendation

// GATE: Human checkpoint before proceeding
```

---

## 🚀 FEATURE DEVELOPMENT (Enhanced with True Parallelization)
Load: workflow-enforcer + worktree-manager + planning-prompts

```bash
// PHASE 0: PLAN (New structured approach)
0a. Create BRIEF.md: Feature scope, success criteria, constraints
0b. /superpowers:brainstorm → Agent mapping + parallelization plan
0c. Create TodoWrite todos → Track in TASK.md
0d. Cost estimate → Flag if expensive

// PHASE 1: SETUP + DB
1a. /database-design:schema-design
1b. /supabase-sql-skill or /database-migrations:sql-migrations
1c. GATE: Schema review before implementation

// PHASE 2: PARALLEL IMPLEMENTATION (Using Worktrees)
// Allocate ports upfront (8100-8199 pool)
// Spawn parallel worktrees with independent agents

PARALLEL_START:
├── Worktree A (ports 8100-8101):
│   └── /python-development:fastapi-pro "Backend [API]"
│
├── Worktree B (ports 8102-8103):
│   └── /frontend-mobile-development:frontend-developer "UI [components]"
│
└── Worktree C (ports 8104-8105):
    └── /unit-testing:test-generate "Test suites"

// Monitor all worktrees
cat ~/.claude/worktree-registry.json | jq '.[] | select(.status == "active")'

PARALLEL_SYNC:
- Wait for all worktrees to complete
- Merge back to main branch (check PR status first)
- Delete worktrees after merge

// PHASE 3: SECURITY + INTEGRATION (Parallel scans)
PARALLEL:
├── 3a. /security-scanning:security-sast
├── 3b. /security-scanning:secrets-scan
├── 3c. /backend-api-security:api-security-audit
└── 3d. Run tests (unit + E2E)

// GATE: ALL must pass
IF (sast_clean AND secrets=0 AND api_secure AND tests=100%):
    → Proceed to Phase 4
ELSE:
    → BLOCK + Fix + Re-scan

// PHASE 4: SHIP (Only if perfect)
4a. /code-review-ai:comprehensive-review
4b. /code-documentation:doc-generate
4c. Update: TASK.md, PLANNING.md, CLAUDE.md
4d. IF clean → git commit + push
4e. Log cost of this feature (if tracking)
```

---

## 🐛 DEBUG MODE (Enhanced with Scientific Method)
Load: debug-like-expert + workflow-enforcer

```bash
// TRIGGER: When standard troubleshooting fails
// MINDSET: Code you wrote is GUILTY until proven innocent

1. CONTEXT SCAN:
   - Detect project type (Python/JS/Rust/etc.)
   - Load domain expertise if available: ~/.claude/skills/expertise/
   - Announce: "Detected [domain] issue → Loading [expertise]"

2. EVIDENCE GATHERING:
   - EXACT error message
   - EXACT reproduction steps
   - ACTUAL vs EXPECTED output
   - Trace execution path

3. HYPOTHESIS FORMATION:
   Hypothesis 1: [cause] → Evidence: [what supports this]
   Hypothesis 2: [cause] → Evidence: [what supports this]
   Hypothesis 3: [cause] → Evidence: [what supports this]

4. SYSTEMATIC TESTING:
   - Test ONE variable at a time
   - Document results
   - Eliminate or confirm each hypothesis

5. ROOT CAUSE + FIX:
   - Minimal change that addresses root cause
   - Document WHY it works
   - Verify original issue resolved
   - Check for regressions

6. OUTPUT FORMAT:
   ## Issue: [Description]
   ### Evidence: [Observations]
   ### Investigation: [What checked, ruled out]
   ### Root Cause: [With evidence]
   ### Solution: [Change and WHY]
   ### Verification: [How confirmed]

// CRITICAL: NO DRIVE-BY FIXES
// If you can't explain WHY, don't commit
```

---

## 🔒 END DAY (Enhanced Security + Context Preservation)
Load: workflow-enforcer + project-context-skill + security-scanning

```bash
// SECURITY SWEEP (MANDATORY - BLOCKS ALL COMMITS)
PARALLEL:
├── 1a. /security-scanning:secrets-scan
├── 1b. /security-scanning:git-history-scan
├── 1c. /security-scanning:dependency-audit --critical-only
├── 1d. /backend-api-security:api-security-audit
└── 1e. /security-scanning:env-audit

// GATE: ALL must pass
IF any_issues:
    → BLOCK commits
    → Fix issues
    → Re-scan
    → Loop until clean

// QUALITY + DOCS
2. /code-review-ai:comprehensive-review
3. /unit-testing:test-generate (for new code)
4. Run full test suite

// CONTEXT PRESERVATION (New - for tomorrow)
5. Update PROJECT_CONTEXT.md:
   - Move today's completed todos to "Done (This Session)"
   - Document blockers encountered
   - Note decisions made and why
   - List tomorrow's priorities

6. Update project docs:
   - TASK.md: Current sprint status
   - PLANNING.md: Roadmap adjustments
   - Backlog.md: New items discovered
   - CLAUDE.md: Any architectural changes

7. /code-documentation:doc-generate "changed-files"

// COST TRACKING (New)
8. If cost tracking enabled:
   - Log today's inference costs
   - Log today's compute costs
   - Update running totals
   - Alert if over budget

// WORKTREE CLEANUP
9. Check for orphaned worktrees:
   cat ~/.claude/worktree-registry.json | jq '.[] | select(.status == "active" and .project == "'$(basename $PWD)'")'
   → Merge or archive completed work
   → Delete merged worktrees

// FINAL OUTPUT
Daily Summary:
├── ✅ Completed: [list]
├── 🔐 Security: [scan results]
├── 📊 Tests: [coverage %]
├── 💰 Cost: [today's spend]
└── 📋 Tomorrow: [top 3 priorities]
```

---

## 🧠 META-ORCHESTRATION (Advanced - LangGraph Patterns)
For multi-agent workflows (from langgraph-agents-skill)

```bash
ORCHESTRATION PATTERN SELECTION:
├── 3-10 agents → Supervisor Pattern (centralized control)
├── 5-15 agents → Swarm Pattern (peer collaboration)
└── 10-30+ agents → Master Pattern (learning systems)

COST-OPTIMIZED ROUTING (from ai-cost-optimizer):
├── Complex reasoning → Claude Sonnet
├── Bulk processing → DeepSeek V3 (90% savings)
├── Code generation → Claude Sonnet
├── Embeddings → Voyage
└── Local dev → Ollama (free)

STATE MANAGEMENT:
- Use TypedDict with Annotated reducers
- add_messages for auto-merge
- Redis distributed locks for parallelization

MIDDLEWARE STACK (from lang-core):
├── Cost tracking (per-task, per-agent)
├── Budget enforcement (stop at threshold)
├── Automatic retry with backoff
├── Response caching
└── PII safety filters
```

---

## 📊 COST TRACKING TEMPLATE
Pattern from lang-core / ai-cost-optimizer

```python
COST_CONFIG = {
    "daily_budget": 5.00,      # Max daily spend
    "monthly_budget": 100.00,  # Max monthly spend
    "alert_threshold": 0.8,    # Alert at 80% of budget

    "model_costs": {
        "claude-sonnet": 0.003,     # per 1K tokens
        "deepseek-v3": 0.00014,     # 95% cheaper
        "qwen-72b": 0.0002,         # 93% cheaper
    },

    "track_by": ["feature", "agent", "day"],
}

# Log after each operation:
# cost_tracker.log(feature="auth", agent="fastapi-pro", tokens=1500, model="deepseek-v3")
```

---

## 🔄 ROLLBACK/RECOVERY PATTERNS
From debug-like-expert methodology

```bash
WHEN TO ROLLBACK:
- Tests failing after "fix"
- Security scan finds new issues
- Performance degradation detected
- Unexpected behavior in production

RECOVERY WORKFLOW:
1. git stash or git stash -u (save current work)
2. git log --oneline -10 (find last known good)
3. git checkout [good-commit] -- [file] (selective rollback)
   OR git revert [bad-commit] (full revert)
4. Run tests to confirm
5. Investigate root cause using debug-like-expert
6. Re-implement with hypothesis testing

WORKTREE RECOVERY:
- If worktree is broken: git worktree remove [path] --force
- Registry cleanup: Edit ~/.claude/worktree-registry.json
- Port release: Ports auto-release on worktree deletion
```

---

## 📁 PROJECT STRUCTURE TEMPLATE

```
project/
├── CLAUDE.md              # Project context for Claude
├── PLANNING.md            # Roadmap, phases, decisions
├── TASK.md                # Current sprint/tasks
├── Backlog.md             # Future work
├── PROJECT_CONTEXT.md     # Session continuity (auto-generated)
├── .taskmaster/
│   └── docs/
│       └── prd.txt        # For task generation
├── .prompts/              # Meta-prompts (from planning-prompts)
│   ├── research/
│   ├── plan/
│   ├── do/
│   └── refine/
├── costs/                 # Cost tracking (optional)
│   ├── daily/
│   └── by-feature/
└── src/                   # Your code
```

---

## 🎯 QUICK REFERENCE COMMANDS

```bash
# Start day
task-master next
cat PROJECT_CONTEXT.md

# Parallel worktrees
git worktree add ../feature-name -b feature/name
cat ~/.claude/worktree-registry.json

# Security sweep
/security-scanning:secrets-scan
/security-scanning:dependency-audit

# Cost check
cat costs/daily/$(date +%Y-%m-%d).json

# End day
git status && git diff --stat
```
