"""
OpenSentinel Life Management Agent — Deep Agent orchestrator.

Architecture:
    tools/      → Atomic, stateless @tool functions (single operations)
    skills/     → SKILL.md instruction files (loaded into subagent prompts)
    subagents/  → Subagent config dictionaries (not pre-created agents)
    agent.py    → Main orchestrator via create_deep_agent

Built on deepagents: filesystem-native, subagent-capable, with human-in-the-loop support.
"""

from pathlib import Path
from typing import Any

from deepagents import create_deep_agent
from langgraph.checkpoint.memory import MemorySaver
from .llm_factory import create_llm

# ── Configuration ───────────────────────────────────────────────────
SKILLS_DIR = Path(__file__).parent / "skills"
PROMPTS_DIR = Path(__file__).parent / "prompts"

# ── LLM Configuration ────────────────────────────────────────────────
# ── Atomic Tools ─────────────────────────────────────────────────────
from .tools import (
    connect_calendar,
    fetch_calendar_events,
    create_calendar_event,
    update_calendar_event,
    suggest_focus_blocks,
    detect_calendar_conflicts,
    connect_email,
    fetch_emails,
    classify_email_intent,
    extract_action_items,
    draft_email_reply,
    send_email,
    create_task,
    update_task,
    fetch_tasks,
    suggest_task_schedule,
    sync_external_tasks,
    detect_critical_action,
    create_approval_card,
    log_action,
    validate_safe_automation,
    get_system_metrics,
    monitor_app_usage,
    check_device_health,
    suggest_system_optimization,
    list_documents,
    read_document,
    search_documents,
    cite_document,
    connect_messenger,
    fetch_messages,
    classify_message_urgency,
    draft_message_reply,
    get_current_weather,
    get_weather_forecast,
    get_hourly_forecast,
    detect_weather_alerts,
    check_precipitation_forecast,
    compare_weather_change,
    search_news,
    get_financial_data,
    analyze_trend,
    get_market_summary,
    search_research_papers,
    get_political_summary,
    search_recipes,
    get_recipe_details,
    get_cooking_tips,
    find_ingredient_stores,
    suggest_ingredient_substitutes,
    search_flights,
    search_trains,
    search_buses,
    get_live_transit_status,
    check_flight_status,
    compare_transport_options,
    browse_webpage,
    search_internet,
    extract_article_text,
    monitor_website_changes,
    search_web,
    generate_summary,
    create_recommendation,
)

# ── Skill Loading ────────────────────────────────────────────────────
def load_skill(skill_name: str) -> str:
    """Load a SKILL.md file from the skills directory."""
    skill_path = SKILLS_DIR / skill_name / "SKILL.md"
    if skill_path.exists():
        return skill_path.read_text(encoding="utf-8")
    return ""

def load_system_prompt(mode: str = "standard") -> str:
    """
    Load modular system prompt to optimize token usage.
    """
    prompt_parts = []
    
    core_path = PROMPTS_DIR / "core.md"
    if core_path.exists():
        prompt_parts.append(core_path.read_text(encoding="utf-8"))
    
    if mode in ("standard", "full"):
        cap_path = PROMPTS_DIR / "capabilities.md"
        if cap_path.exists():
            prompt_parts.append(cap_path.read_text(encoding="utf-8"))
        
        safety_path = PROMPTS_DIR / "safety.md"
        if safety_path.exists():
            prompt_parts.append(safety_path.read_text(encoding="utf-8"))
    
    if mode == "full":
        quality_path = PROMPTS_DIR / "quality_standards.md"
        if quality_path.exists():
            prompt_parts.append(quality_path.read_text(encoding="utf-8"))
    
    if not prompt_parts:
        return (
            "You are OpenSentinel, a proactive AI agent for life management. "
            "You help with daily planning, research, productivity, and personal coordination. "
            "Use tools to interact with external systems and delegate to subagents for complex tasks."
        )
    
    return "\n\n---\n\n".join(prompt_parts)

# ── Subagent Configurations ──────────────────────────────────────────
# Define subagents as CONFIGS (dictionaries), not pre-created agents

def create_subagent_configs() -> list[dict[str, Any]]:
    """Create subagent configuration dictionaries for create_deep_agent."""
    
    # Personal Planning Subagents
    scheduling_coordinator = {
        "name": "scheduling_coordinator",
        "description": "Optimizes calendar layouts, resolves conflicts, and suggests focus blocks. Use for complex scheduling decisions.",
        "system_prompt": load_skill("smart-scheduling") or (
            "You are a scheduling specialist. Analyze calendars, suggest optimal meeting times, "
            "resolve conflicts, and create focus blocks. Always check for conflicts before creating events. "
            "Return structured recommendations with reasoning."
        ),
        "tools": [
            fetch_calendar_events,
            create_calendar_event,
            update_calendar_event,
            detect_calendar_conflicts,
            suggest_focus_blocks,
        ],
        # Uses parent agent's model if not specified
    }
    
    email_triage_specialist = {
        "name": "email_triage_specialist",
        "description": "Classifies emails, extracts action items, and drafts responses. Use for inbox processing.",
        "system_prompt": load_skill("email-triage") or (
            "You are an email management specialist. Classify emails by urgency and intent, "
            "extract actionable tasks, and draft appropriate replies. Prioritize based on sender importance "
            "and content urgency. Return a structured triage report."
        ),
        "tools": [
            fetch_emails,
            classify_email_intent,
            extract_action_items,
            draft_email_reply,
            create_task,
        ],
    }
    
    task_strategist = {
        "name": "task_strategist",
        "description": "Analyzes task lists and suggests prioritization strategies. Use for task management.",
        "system_prompt": (
            "You are a productivity strategist. Analyze task lists, suggest prioritization frameworks "
            "(Eisenhower matrix, energy-based scheduling), and identify task dependencies. "
            "Consider deadlines, energy levels, and context switching costs."
        ),
        "tools": [
            fetch_tasks,
            create_task,
            update_task,
            suggest_task_schedule,
        ],
    }
    
    daily_briefing_compiler = {
        "name": "daily_briefing_compiler",
        "description": "Compiles daily briefings from calendar, weather, tasks, and news. Use for morning briefings.",
        "system_prompt": load_skill("daily-briefing") or (
            "You are a daily briefing specialist. Compile information from multiple sources "
            "(calendar, weather, tasks, news) into a concise, actionable morning briefing. "
            "Prioritize by urgency and impact. Use markdown formatting."
        ),
        "tools": [
            fetch_calendar_events,
            get_current_weather,
            fetch_tasks,
            search_news,
            generate_summary,
        ],
    }
    
    # Research & Knowledge Subagents
    research_analyst = {
        "name": "research_analyst",
        "description": "Deep research on finance, tech, science, or politics. Use for comprehensive research tasks.",
        "system_prompt": (
            "You are a research analyst. Conduct thorough research using multiple sources, "
            "verify facts, analyze trends, and synthesize findings into structured reports. "
            "Always cite sources and indicate confidence levels."
        ),
        "tools": [
            search_news,
            get_financial_data,
            analyze_trend,
            get_market_summary,
            search_research_papers,
            get_political_summary,
            search_internet,
            extract_article_text,
            generate_summary,
        ],
    }
    
    report_generator = {
        "name": "report_generator",
        "description": "Compiles data into formatted reports. Use for creating summaries and briefings.",
        "system_prompt": (
            "You are a report writing specialist. Compile information into well-structured, "
            "readable reports with executive summaries, key findings, and actionable recommendations. "
            "Use markdown formatting for clarity."
        ),
        "tools": [
            generate_summary,
            create_recommendation,
            cite_document,
            read_document,
        ],
    }
    
    # Life Management Subagents
    weather_advisor = {
        "name": "weather_advisor",
        "description": "Analyzes weather patterns and suggests preparations. Use for weather-related planning.",
        "system_prompt": (
            "You are a weather planning specialist. Analyze forecasts, detect alerts, and suggest "
            "preparations for weather conditions. Consider travel impacts, outdoor activities, and safety."
        ),
        "tools": [
            get_current_weather,
            get_weather_forecast,
            get_hourly_forecast,
            detect_weather_alerts,
            check_precipitation_forecast,
            compare_weather_change,
        ],
    }
    
    culinary_advisor = {
        "name": "culinary_advisor",
        "description": "Recipe suggestions, cooking tips, and ingredient sourcing. Use for meal planning.",
        "system_prompt": (
            "You are a culinary assistant. Suggest recipes based on preferences/dietary restrictions, "
            "provide cooking tips, find ingredient sources, and suggest substitutions. "
            "Consider nutrition, prep time, and skill level."
        ),
        "tools": [
            search_recipes,
            get_recipe_details,
            get_cooking_tips,
            find_ingredient_stores,
            suggest_ingredient_substitutes,
        ],
    }
    
    travel_coordinator = {
        "name": "travel_coordinator",
        "description": "Coordinates flights, trains, buses, and transit. Use for travel planning.",
        "system_prompt": (
            "You are a travel planning specialist. Search and compare transport options, "
            "check live status, and coordinate multi-leg journeys. Optimize for cost, time, and convenience. "
            "Alert about delays or disruptions."
        ),
        "tools": [
            search_flights,
            search_trains,
            search_buses,
            get_live_transit_status,
            check_flight_status,
            compare_transport_options,
        ],
    }
    
    # Safety Subagent
    approval_gatekeeper = {
        "name": "approval_gatekeeper",
        "description": "Reviews critical actions requiring human approval. Use for sensitive operations.",
        "system_prompt": load_skill("approval-workflow") or (
            "You are a safety reviewer. Analyze actions for potential risks, verify safety constraints, "
            "and prepare approval requests with clear risk/benefit analysis. Never proceed without explicit approval "
            "for destructive or high-impact operations."
        ),
        "tools": [
            detect_critical_action,
            create_approval_card,
            validate_safe_automation,
            log_action,
        ],
    }
    
    return [
        scheduling_coordinator,
        email_triage_specialist,
        task_strategist,
        daily_briefing_compiler,
        research_analyst,
        report_generator,
        weather_advisor,
        culinary_advisor,
        travel_coordinator,
        approval_gatekeeper,
    ]

# ── Agent Factory ────────────────────────────────────────────────────
def create_agent(
    llm: Any = None,
    prompt_mode: str = "standard",
    enable_human_in_the_loop: bool = True,
) -> Any:
    """
    Create the OpenSentinel orchestrator agent.
    
    Args:
        llm: Pre-configured LLM instance (orchestrator default is used if None)
        prompt_mode: System prompt complexity ("minimal", "standard", "full")
        enable_human_in_the_loop: Whether to require approval for sensitive operations
    
    Returns:
        Configured deep agent instance
    """
    
    model = llm if llm is not None else create_llm()
    
    # All atomic tools available to agent
    tools = [
        # Calendar
        connect_calendar,
        fetch_calendar_events,
        create_calendar_event,
        update_calendar_event,
        suggest_focus_blocks,
        detect_calendar_conflicts,
        # Email
        connect_email,
        fetch_emails,
        classify_email_intent,
        extract_action_items,
        draft_email_reply,
        send_email,
        # Tasks
        create_task,
        update_task,
        fetch_tasks,
        suggest_task_schedule,
        sync_external_tasks,
        # Safety
        detect_critical_action,
        create_approval_card,
        log_action,
        validate_safe_automation,
        # System
        get_system_metrics,
        monitor_app_usage,
        check_device_health,
        suggest_system_optimization,
        # Documents
        list_documents,
        read_document,
        search_documents,
        cite_document,
        # Messaging
        connect_messenger,
        fetch_messages,
        classify_message_urgency,
        draft_message_reply,
        # Weather
        get_current_weather,
        get_weather_forecast,
        get_hourly_forecast,
        detect_weather_alerts,
        check_precipitation_forecast,
        compare_weather_change,
        # Research
        search_news,
        get_financial_data,
        analyze_trend,
        get_market_summary,
        search_research_papers,
        get_political_summary,
        # Culinary
        search_recipes,
        get_recipe_details,
        get_cooking_tips,
        find_ingredient_stores,
        suggest_ingredient_substitutes,
        # Transport
        search_flights,
        search_trains,
        search_buses,
        get_live_transit_status,
        check_flight_status,
        compare_transport_options,
        # Web
        browse_webpage,
        search_internet,
        extract_article_text,
        monitor_website_changes,
        search_web,
        generate_summary,
        create_recommendation,
    ]
    
    instructions = load_system_prompt(mode=prompt_mode)
    subagents = create_subagent_configs()
    
    # Human-in-the-loop configuration using interrupt_on
    interrupt_on = {}
    if enable_human_in_the_loop:
        interrupt_on = {
            "send_email": True,  # Full HITL (approve/edit/reject)
            "create_calendar_event": True,
            "update_calendar_event": True,
            "delete_file": {"allowed_decisions": ["approve", "reject"]},  # Custom restrictions
        }
    
    # Required checkpointer for HITL
    checkpointer = MemorySaver()
    
    agent = create_deep_agent(
        tools=tools,
        instructions=instructions,
        model=model,
        subagents=subagents,  # List of config dicts, not pre-created agents
        interrupt_on=interrupt_on if enable_human_in_the_loop else None,
        checkpointer=checkpointer,
    )
    
    return agent
