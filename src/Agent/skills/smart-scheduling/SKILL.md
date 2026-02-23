---
name: smart-scheduling
description: "Calendar optimization and conflict resolution. Detect scheduling conflicts, suggest focus blocks, map tasks to calendar slots, and create approval cards for calendar changes."
---

# Smart Scheduling Skill

Optimize calendar for maximum productivity and minimal conflicts.

## Steps

1. **Fetch Current Calendar** — Use `fetch_calendar_events` with:
   - `start_date`: start of date range (user-specified or today)
   - `end_date`: end of date range (user-specified or +7 days)
   - `calendar_id`: "primary"

   Parse events and identify busy/free slots

2. **Detect Conflicts** — Use `detect_calendar_conflicts` with:
   - `date_range`: from step 1

   Identify:
   - Double-bookings
   - Back-to-back meetings (no buffer time)
   - Overlapping commitments
   - Travel time violations

3. **Suggest Focus Blocks** — Use `suggest_focus_blocks` with:
   - `date`: each day in range
   - `min_duration_minutes`: 90 (configurable for deep work)

   Find optimal slots for focused work based on:
   - Time of day (morning > afternoon for focus)
   - Surrounding context (avoid sandwich between meetings)
   - Minimum continuous duration

4. **Fetch Pending Tasks** — Use `fetch_tasks` with:
   - `status`: "pending"
   - `priority`: "urgent" and "high"

   Get tasks needing scheduling

5. **Suggest Task Schedule** — Use `suggest_task_schedule` with:
   - `task_ids`: from step 4
   - `date_range`: from step 1

   Map tasks to available calendar slots based on:
   - Effort estimates
   - Deadlines
   - Priority
   - Energy levels (morning for high-priority)

6. **Evaluate Each Suggestion** — For each proposed change:
   - Use `detect_critical_action` to check if requires approval
   - Calendar changes are ALWAYS critical
   - Use `create_approval_card` for each proposed event

7. **Compile Optimized Schedule** — Generate proposed schedule with:
   - Conflict resolutions
   - Focus blocks highlighted
   - Task-to-timeslot mappings
   - Approval cards for all changes

## Output Format

Return structured optimization plan:

```markdown
## Smart Scheduling Optimization — [Date Range]

### Conflicts Detected (X items)
1. **Double-booking on 2026-02-22 at 10:00 AM**
   - Event A: Team Meeting
   - Event B: Client Call
   - **Suggestion**: Reschedule Client Call to 11:00 AM
   - [Approval Card]

### Suggested Focus Blocks
- **Mon 2026-02-22**: 10:00-12:00 (2 hrs) — Morning deep work slot
- **Wed 2026-02-24**: 09:00-11:00 (2 hrs) — Peak focus time
- **Fri 2026-02-26**: 14:00-16:00 (2 hrs) — Afternoon project time

### Task Scheduling Recommendations
1. **"Review budget proposal"** (30 min, high priority)
   - Suggested slot: Tue 2026-02-23 at 10:00-10:30
   - Reasoning: Morning slot, aligns with Friday deadline
   - [Approval Card]

2. **"Update project docs"** (1 hr, medium priority)
   - Suggested slot: Wed 2026-02-24 at 11:00-12:00
   - Reasoning: After focus block, before lunch
   - [Approval Card]

### Summary
- Conflicts resolved: X
- Focus blocks added: Y
- Tasks scheduled: Z
- Total approval cards: N
```

## Quality Rules

- **ALWAYS require approval** for calendar modifications
- **Respect focus hours**: Don't schedule meetings during deep work slots
- **Include buffer time**: 10-15 min between meetings
- **Minimize context switching**: Batch similar activities
- **Energy-aware**: High-priority tasks in morning, routine in afternoon
- **Max 3 options**: Don't overwhelm with choices

## Error Handling

- If calendar fetch fails → Cannot proceed, return error
- If conflict detection fails → Continue with focus blocks only
- If task scheduling fails → Show focus blocks and conflicts only
- Log all proposed changes with `log_action`
