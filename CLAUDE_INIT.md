# Claude Code Initialization Instructions

This file defines the standard agent workflow for all development sessions in this project.

## Agent Workflow Pattern

When starting any development task, use this mandatory sequence:

### 1. Sequential Thinking (MCP)
**Purpose**: Break down complex tasks into logical steps before execution
**Tool**: `mcp__sequential-thinking__sequentialthinking`

Use this MCP to:
- Analyze the task requirements
- Identify dependencies and prerequisites
- Plan the step-by-step approach
- Generate solution hypotheses
- Verify hypotheses before implementation

**Example Usage**:
```
Before writing code or making changes, use Sequential Thinking to:
1. Understand the problem space
2. Identify edge cases
3. Plan implementation steps
4. Verify the approach makes sense
```

### 2. Serena (MCP)
**Purpose**: Semantic code navigation and intelligent file operations
**Tool**: `mcp__serena__*` family of tools

Use Serena for:
- Finding symbols and code structures (`find_symbol`)
- Understanding code relationships (`find_referencing_symbols`)
- Reading only necessary code (`get_symbols_overview`)
- Symbol-based editing (`replace_symbol_body`, `insert_after_symbol`)
- Pattern-based search (`search_for_pattern`)

**Key Principles**:
- ✅ Always activate project first: `mcp__serena__activate_project`
- ✅ Read memories to understand project context
- ✅ Use symbolic tools instead of reading entire files
- ✅ Only read bodies when necessary for the task
- ❌ Never read entire files unnecessarily
- ❌ Never read the same content multiple times

**Example Workflow**:
```
1. Activate project: mcp__serena__activate_project("dealer-scraper-mvp")
2. Read relevant memories: mcp__serena__list_memories() → read if relevant
3. Get symbols overview: mcp__serena__get_symbols_overview("path/to/file.py")
4. Find specific symbols: mcp__serena__find_symbol("ClassName/method_name")
5. Edit with precision: mcp__serena__replace_symbol_body() or regex tools
```

### 3. Context7 (MCP)
**Purpose**: Retrieve up-to-date library documentation and code examples
**Tool**: `mcp__context7__resolve-library-id` + `mcp__context7__get-library-docs`

Use Context7 when:
- Working with external libraries (Playwright, Selenium, etc.)
- Need current API documentation
- Looking for library-specific patterns
- Verifying method signatures and parameters

**Example Usage**:
```
1. Resolve library: mcp__context7__resolve-library-id("playwright")
2. Get docs: mcp__context7__get-library-docs("/microsoft/playwright")
```

## Specialized Subagents

Use Claude Code's Task tool with specialized subagents for specific domains:

### Available Subagents (User Agents - ~/.claude/agents/)
1. **ai-systems-architect**: Multi-agent systems, LLM routing, RAG pipelines
2. **api-design-expert**: REST/GraphQL API design, OpenAPI specs
3. **data-pipeline-engineer**: ETL/ELT, Airflow, Kafka, data infrastructure
4. **developer-experience-engineer**: CLI tools, documentation, dev productivity
5. **fullstack-mvp-engineer**: Rapid TypeScript/React/Next.js prototypes
6. **infrastructure-devops-engineer**: Terraform, Kubernetes, CI/CD
7. **react-performance-optimizer**: Core Web Vitals, bundle size, rendering optimization
8. **realtime-systems-optimizer**: WebSocket, low-latency systems
9. **security-compliance-engineer**: OAuth, encryption, GDPR, PCI-DSS
10. **testing-automation-architect**: Test strategies, frameworks, coverage

### Superpowers Subagents (Built-in Skills)
- **superpowers:brainstorming**: Refine ideas before implementation
- **superpowers:test-driven-development**: Write tests first, then code
- **superpowers:systematic-debugging**: Four-phase debugging framework
- **superpowers:code-reviewer**: Review completed work against plan
- **superpowers:verification-before-completion**: Verify before claiming done
- **superpowers:using-git-worktrees**: Isolated feature branches
- **superpowers:writing-plans**: Create detailed implementation plans

### Subagent Usage Pattern
```
# Use Task tool with appropriate subagent
Task tool → subagent_type="security-compliance-engineer"
         → prompt="Review authentication implementation for security vulnerabilities"
```

## Verification Workflow

### During Development
- Mark todos as `in_progress` before starting work
- Mark todos as `completed` IMMEDIATELY after finishing each task
- Use **TodoWrite** to track all multi-step work

### Before Completion
**MANDATORY**: Use task-checker verification pattern:

1. **Run all verification commands**:
   ```bash
   # Example verifications
   python3 -m pytest tests/
   python3 scripts/validate_data.py
   git status
   ```

2. **Review outputs** - Don't claim success without evidence

3. **Use verification skill**:
   ```
   Skill(superpowers:verification-before-completion)
   ```

4. **Only if all checks pass** → Proceed to git commit

### Task-Checker Pattern
After completing a major piece of work:
1. Use `Task` tool with appropriate reviewer subagent
2. Pass ALL context (what was implemented, why, how)
3. Review feedback critically
4. Address any issues found
5. Re-verify before proceeding

## Git Automation Requirements

### Commit Standards
**Format**: `Type: Short description`

**Types**:
- `Feature`: New functionality
- `Fix`: Bug fixes
- `Cleanup`: Refactoring, technical debt removal
- `Docs`: Documentation updates
- `Config`: Configuration changes

**Examples**:
```
Feature: Enphase manual collection workflow scripts
Fix: Progress tracker JSON format validation
Cleanup: Remove deprecated scraper utilities
Docs: Update CLAUDE.md with new OEM scrapers
```

### Commit Workflow
```bash
# 1. Check status
git status

# 2. Add files
git add <files>

# 3. Commit with descriptive message
git commit -m "Type: Description

Additional context if needed (why, not just what)

🤖 Generated with Claude Code"

# 4. Push to GitHub
git push origin main
```

### Pre-Commit Checklist
- [ ] All tests pass (if applicable)
- [ ] Verification commands run successfully
- [ ] TodoWrite todos marked as completed
- [ ] Task-checker subagent approved work
- [ ] Git status reviewed
- [ ] Commit message describes business value (not just technical changes)

## Project-Specific Context

### Current Development State
- **Tesla**: 70 Premier installers collected (COMPLETE ✅)
- **Enphase**: 28 Platinum/Gold installers from 3 ZIPs (IN PROGRESS ⏳)
- **Manual Collection Method**: 1-ZIP-at-a-time using MCP Playwright
- **Target**: 40 ZIPs total (matching Tesla collection)

### Active Memories
Check `mcp__serena__list_memories()` at session start:
- `tesla-scraper-current-status`: Tesla Browserbase scraper status
- `browserbase-authentication-fix`: Critical auth fix pattern

### Key Files
- **Collection Scripts**: `scripts/*_manual_collection.py`
- **Append Scripts**: `scripts/append_*_installer.py`
- **Deduplication**: `scripts/deduplicate_*_installers.py`
- **Master Lists**: `output/*_deduped_*.csv`
- **Progress Trackers**: `output/*_progress.json`

## MCP Usage Best Practices

### Sequential Thinking
- Always use for tasks with 3+ steps
- Generate hypotheses before implementation
- Verify hypotheses before proceeding
- Adjust total_thoughts as you progress

### Serena
- Activate project at session start
- Read project memories if relevant to task
- Use symbolic tools over file reads
- Prefer regex for small edits, symbols for large changes
- Never read entire files unnecessarily

### Context7
- Use before working with external libraries
- Review docs BEFORE subagents start work
- Verify library versions match project dependencies

## Anti-Patterns to Avoid

❌ **DON'T**:
- Start coding without Sequential Thinking
- Read entire files when only need specific symbols
- Use bash cat/grep when Serena tools available
- Skip verification before claiming work done
- Make git commits without running verification
- Batch complete multiple todos at once
- Use placeholders in tool calls

✅ **DO**:
- Follow MCP order: Sequential Thinking → Serena → Context7
- Mark todos as in_progress before starting
- Mark todos as completed IMMEDIATELY after finishing
- Use specialized subagents for domain-specific work
- Run verification commands before claiming success
- Write descriptive git commit messages
- Provide evidence of success (command outputs)

## Session Startup Checklist

At the start of EVERY session:

1. [ ] Activate Serena project: `mcp__serena__activate_project("dealer-scraper-mvp")`
2. [ ] List and read relevant memories
3. [ ] Review git status to understand current state
4. [ ] Check TodoWrite todos (create if starting new work)
5. [ ] Use Sequential Thinking for task breakdown
6. [ ] Review Context7 docs if using external libraries
7. [ ] Launch appropriate subagents for specialized work

## Summary

This project uses a **verified, multi-agent workflow** with mandatory MCP usage:

1. **Think First**: Sequential Thinking MCP
2. **Navigate Smartly**: Serena symbolic tools
3. **Stay Current**: Context7 for library docs
4. **Specialize**: Task tool with domain-specific subagents
5. **Verify Always**: Verification skill + task-checker pattern
6. **Track Progress**: TodoWrite for all multi-step work
7. **Commit Right**: Descriptive messages + evidence of success

**Remember**: The overhead of following this process is tiny compared to the cost of:
- Missing steps
- Reading unnecessary code
- Making errors from outdated docs
- Claiming success without verification
- Creating commits without proper testing
