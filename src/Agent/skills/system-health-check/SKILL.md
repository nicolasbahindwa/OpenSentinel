---
name: system-health-check
description: "Device health monitoring and optimization recommendations. Checks CPU, memory, disk, battery, and app usage, then suggests actionable improvements."
---

# System Health Check Skill

Monitor device performance and provide optimization recommendations.

## Steps

1. **Get System Metrics** — Use `get_system_metrics` with:
   - `metric_types`: "all"

   Retrieve:
   - CPU usage and temperature
   - Memory (total, used, available)
   - Disk space (total, used, free)
   - Battery level and charging status
   - Network connectivity

2. **Monitor App Usage** (if enabled) — Use `monitor_app_usage` with:
   - `date_range`: "today" or user-specified

   Get:
   - Top apps by focus time
   - Application switch count
   - Total focus time

3. **Check Device Health** — Use `check_device_health`:
   - Detect alerts (high memory, thermal events, low disk space)
   - Assess overall health status
   - Identify performance bottlenecks

4. **Analyze Metrics** — Evaluate each category:

   **CPU:**
   - If usage > 80%: Flag high CPU, identify heavy processes
   - If temperature > 80°C: Thermal warning

   **Memory:**
   - If usage > 70%: Recommend closing apps
   - If usage > 85%: Urgent optimization needed

   **Disk:**
   - If usage > 80%: Recommend cleanup
   - If usage > 90%: Critical space warning

   **Battery:**
   - If < 20% and not charging: Low battery alert
   - Estimate time remaining

5. **Generate Optimization Suggestions** — Use `suggest_system_optimization` with:
   - `metrics`: JSON from step 1

   Get actionable recommendations

6. **Compile Health Report** — Generate structured summary

## Output Format

Return health report with alerts and recommendations:

```markdown
## Device Health Report — [Date Time]

### Health Status: [Healthy | Warning | Critical]

### System Metrics

**CPU**
- Usage: 45% (8 cores)
- Temperature: 65°C
- Status: ✅ Normal

**Memory**
- Total: 16 GB
- Used: 10.5 GB (65%)
- Available: 5.5 GB
- Status: ⚠️ Moderate usage

**Disk**
- Total: 512 GB
- Used: 320 GB (62%)
- Free: 192 GB
- Status: ✅ Adequate space

**Battery**
- Level: 78%
- Charging: No
- Time Remaining: ~4.2 hours
- Status: ✅ Good

**Network**
- Download: 45 Mbps
- Upload: 12 Mbps
- Status: ✅ Connected

### Alerts (if any)

⚠️ **Memory Warning**
- Memory usage at 65% — consider closing unused applications
- Impact: Moderate (may slow performance)

### App Usage (Today)

1. VS Code — 3h 5min (12 switches)
2. Chrome — 1h 35min (34 switches)
3. Slack — 42min (18 switches)
4. Zoom — 1h (3 switches)

**Analysis:** High context switching in Chrome (34 switches). Consider batching web tasks.

### Optimization Recommendations

**Priority: Medium**
1. **Close unused browser tabs**
   - Reason: Memory usage above 60%
   - Impact: Free ~2GB memory
   - Est. Time: 2 minutes

**Priority: Low**
2. **Clear disk cache and temp files**
   - Reason: Disk usage above 60%
   - Impact: Free ~5-10GB storage
   - Est. Time: 5 minutes

### Summary
- Overall Status: Warning (1 alert)
- Recommended Actions: 2
- Next Check: Tomorrow morning
```

## Quality Rules

- **Threshold-based alerts**: Clear criteria (CPU > 80%, Memory > 70%, etc.)
- **Actionable recommendations**: Specific steps, not vague advice
- **Impact estimates**: Quantify expected improvements
- **Time estimates**: How long each optimization takes
- **Prioritized**: High/Medium/Low based on urgency
- **Opt-in for app monitoring**: Respect user privacy preferences

## Error Handling

- If metrics fetch fails → Return "Unable to retrieve metrics", suggest manual check
- If app usage disabled → Skip that section, note in output
- If health check fails → Use available data only, note limitations
