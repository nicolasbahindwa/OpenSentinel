---
name: retrieval-synthesis-skill
description: Combine tool outputs, files, and retrieved evidence into a grounded synthesis without losing provenance or introducing unsupported conclusions
---

# Retrieval Synthesis Skill

Use this skill when the answer must combine multiple sources or tool outputs.

## Workflow

1. **Gather the relevant artifacts** - Collect all tool outputs, search results, file contents
2. **Normalize into key facts** - Extract the essential information from each source
3. **Remove duplicates and note contradictions** - Deduplicate and flag conflicts
4. **Structure by topic** - Organize facts into logical sections/categories
5. **Build the answer with source attribution** - Cite where each fact came from
6. **Add context and explanation** - Don't just list facts, explain what they mean

## Source Attribution (REQUIRED)

**CRITICAL: Cite the ACTUAL external source, NOT the tool name!**

**Every factual claim MUST include its REAL source:**
- ❌ WRONG: `(Source: weather_lookup)` or `(Source: internet_search)`
- ✅ CORRECT: `(Source: Open-Meteo API)` or `(Source: JR East website)`

**How to find real sources:**
1. **Weather data** → Look for API name in tool output → cite "Open-Meteo API" or "Weather.com"
2. **Currency data** → cite "Frankfurter API" or "European Central Bank" or "Exchange Rates API"
3. **Web searches** → Extract website name from URL → "JR East", "Tokyo Disney Resort", "BBC News", etc.
4. **Files** → cite filename: `(Source: config.yaml)` or `(Source: user_prefs.txt)`
5. **Stock/crypto** → cite "Yahoo Finance", "CoinGecko API", etc.

**Citation placement:**
- Place citations immediately after each claim
- For a section with multiple facts from one source, cite once at section end
- Never present facts without attribution

## Structure Guidelines

**For multi-part answers, organize with:**
1. **Section headers** - Group related information (e.g., "Weather", "Transport", "Currency")
2. **Context first** - Explain what the data means before citing raw numbers
3. **Connections** - Link related information (weather → clothing advice)
4. **Actionable advice** - End with helpful recommendations

## Rules

- **ALWAYS cite sources** - Never present facts without attribution
- **Prefer synthesis over dump-style summaries** - Organize and explain, don't just list
- **Keep source attribution attached to claims** - Citations must be inline, not at the end
- **Resolve contradictions when possible** - If sources conflict, acknowledge and explain
- **Avoid filling gaps with speculation** - If information is missing, state uncertainty explicitly
- **Provide context** - Explain what numbers/facts mean in practical terms

## Example

❌ WRONG (no sources, dump-style):
"Temperature is 13°C. USD/EUR is 0.87. Transport costs ¥550-800."

❌ WRONG (using tool names as sources):
"Temperature is 13°C (Source: weather_lookup). USD/EUR is 0.87 (Source: currency). Transport costs ¥550-800 (Source: internet_search)."

✅ CORRECT (structured with REAL sources):

"**Weather**
It's gonna be cool at around 13-14°C with some light rain expected (Source: Open-Meteo API). That's sweater weather - not freezing, but definitely not warm!

**Currency Rates**
The dollar to euro exchange rate is currently at 0.87 USD/EUR (Source: Frankfurter API), so $100 gets you about €87.

**Transport Cost**
Getting from Kashiwa to Tokyo station will run you about ¥550-800 (roughly $5-7 USD), and the journey takes around 37 minutes (Source: JR East website)."

End of Skill.
