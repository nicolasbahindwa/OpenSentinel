# Workflow Orchestration — AI Agent Optimized

> Purpose: Ensure reliable, verifiable, low-regression autonomous execution by AI coding agents.

---

# Operating Modes

The agent MUST operate in exactly one mode at a time.

- **FAST PATH** — for trivial, low-risk changes  
- **PLAN MODE (Default)** — for all non-trivial work  
- **INCIDENT MODE** — when failures or uncertainty arise  

If unsure which mode applies → use PLAN MODE.

---

## Fast Path Eligibility

Agent MAY skip planning ONLY if ALL conditions are true:

- ≤10 lines of code changed  
- No new files created  
- No architectural impact  
- Existing tests cover affected code  
- No external system interaction  

If ANY condition fails → switch to PLAN MODE.

---

# 1. Plan Mode (Default)

## Entry Criteria

Enter PLAN MODE when ANY are true:

- ≥3 implementation steps  
- Architectural decision required  
- Requirements unclear or incomplete  
- Multiple files affected  
- External I/O involved  
- Tests missing or insufficient  

---

## Required Plan Artifacts

Before implementation, the agent MUST produce:

```md
### Plan Summary
### Files to Change
### Risks
### Test Strategy
### Success Criteria
```

---

## Plan Exit Checklist

All must be verified before coding:

* [ ] Requirements understood
* [ ] Edge cases identified
* [ ] Failure modes considered
* [ ] Test approach defined
* [ ] Scope bounded and minimal

If any item is unchecked → DO NOT IMPLEMENT.

---

# 2. Context & Token Discipline

## Context Budget Rules

The agent MUST:

* Load only relevant context
* Prefer partial file reads over full files
* Summarize large artifacts before reasoning
* Avoid redundant context loading
* Keep the main context window clean

---

## Subagent Strategy

Use subagents for:

* research and exploration
* large file analysis
* parallel comparisons
* log analysis

### Hard Constraints

* One task per subagent
* Subagents must return structured output
* Main agent performs final synthesis
* Do not spawn subagents unnecessarily

---

# 3. Implementation Protocol

## Change Strategy (Priority Order)

The agent MUST prefer:

1. Minimal diff
2. Localized change
3. Backward-compatible solution
4. Refactor ONLY when required

---

## Forbidden Behaviors

The agent MUST NOT:

* Rewrite large files without necessity
* Mix refactor and feature work in one change
* Introduce speculative improvements
* Modify unrelated code
* Silence errors without handling
* Add temporary fixes without tracking

---

# 4. Verification Before Completion (P0)

A task is NOT complete until ALL pass:

* [ ] Code compiles or runs
* [ ] Existing tests pass
* [ ] New tests added when required
* [ ] Happy path verified
* [ ] Edge cases covered
* [ ] No new warnings or errors in logs
* [ ] Diff reviewed for unintended changes

---

## Staff Engineer Gate

The agent MUST ask:

> "Would a staff engineer approve this change?"

If confidence is low → refine the solution.

---

# 5. Autonomous Bug Fixing

## Trigger Conditions

Enter bug-fix flow when:

* Tests fail
* Runtime error detected
* CI failure observed
* User reports a defect

---

## Required Bug Workflow

The agent MUST:

1. Reproduce the issue
2. Identify root cause
3. Add failing test (when possible)
4. Implement minimal fix
5. Verify the fix
6. Update lessons

---

## Hard Rule

Do NOT ask the user for information that can be derived from:

* logs
* stack traces
* repository code
* existing tests

---

# 6. Incident Mode (Failure Recovery)

## Trigger Conditions

Activate INCIDENT MODE when:

* Repeated failures occur
* Unexpected side effects appear
* Correctness is uncertain
* Requirements conflict

---

## Incident Procedure

1. STOP new feature work
2. Summarize the failure clearly
3. Form root-cause hypotheses
4. Gather missing evidence
5. Apply minimal corrective fix
6. Re-verify the full system

---

# 7. Self-Improvement Loop

After ANY user correction, the agent MUST update:

```
tasks/lessons.md
```

---

## Lesson Entry Format

```md
### Mistake Pattern
### Root Cause
### Prevention Rule
### Detection Signal
```

---

## Session Start Rule

At the start of related work, the agent MUST:

* Review relevant lessons
* Apply prevention rules proactively

---

# 8. Anti-Hallucination Safeguards

The agent MUST NOT:

* Invent file contents
* Assume APIs without evidence
* Guess schema fields
* Fabricate test results
* Claim execution that did not occur

---

## When Information Is Missing

The agent MUST:

1. State uncertainty explicitly
2. Inspect the repository when possible
3. Request the minimal missing information if required

Never guess silently.

---

# 9. Task Management Protocol

For all PLAN MODE work:

1. **Plan First** — Write plan to `tasks/todo.md` with checkable items
2. **Verify Plan** — Validate before implementation
3. **Track Progress** — Mark items complete incrementally
4. **Explain Changes** — Provide high-level summary per step
5. **Document Results** — Add review section to `tasks/todo.md`
6. **Capture Lessons** — Update `tasks/lessons.md` after corrections

---

# 10. Completion Criteria

A task is COMPLETE only when:

* [ ] Success criteria met
* [ ] Verification checklist fully passed
* [ ] No known regressions introduced
* [ ] Changes documented
* [ ] Lessons captured (if applicable)

---

# 11. Engineering Principles

## Simplicity First

* Prefer the smallest correct solution
* Optimize for readability over cleverness
* Avoid premature abstraction

---

## Root Cause Discipline

* Fix causes, not symptoms
* No temporary fixes without tracking
* No TODOs without issue reference

---

## Minimal Impact Rule

Changes MUST:

* Touch the fewest files possible
* Avoid public API breakage
* Preserve backward compatibility

---

# 12. Execution Mindset

The agent operates as:

* cautious before coding
* aggressive in verification
* minimal in changes
* explicit about uncertainty
* relentless about root cause

---

**End of Specification**
