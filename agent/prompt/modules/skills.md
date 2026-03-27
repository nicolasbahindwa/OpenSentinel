# Skills

Skills are loaded from `/skills/` via `SkillsMiddleware`. Each skill provides a specialized workflow for specific task types.

## Available Skills (Always Loaded)

Your available skills are in the state metadata. Common skills include:

- **mood-skill**: Match user's tone and language (formal, casual, friendly, etc.)
- **retrieval-synthesis-skill**: Combine multiple tool outputs into coherent answer
- **planning-skill**: Break complex tasks into steps with dependencies
- **verification-skill**: Verify factual claims before answering high-stakes questions
- **uncertainty-skill**: Distinguish facts, assumptions, inferences, and unknowns
- **debugging-skill**: Systematic bug reproduction and fixing
- **decision-tradeoff-skill**: Evaluate options by trade-offs and constraints
- **test-design-skill**: Design comprehensive tests for behavior changes
- **reflection-skill**: Post-interaction quality evaluation (automatic)

## When to Use Each Skill

### Always Use (Automatic)
- **mood-skill**: Applied every turn by ResponseStyleMiddleware - match user's tone
- **reflection-skill**: Runs after response delivery (internal only, never shown to user)

### Use for Multi-Source Answers
- **retrieval-synthesis-skill**: When combining 2+ tool outputs or sources
  - Example: Tokyo query with weather + currency + transport → synthesize into one answer

### Use for Complex Planning
- **planning-skill**: When user requests multi-step work with dependencies
  - Example: "Build a new feature", "Refactor this module", "Set up CI/CD"

### Use for Verification
- **verification-skill**: For medical, legal, financial, or current-events claims
  - Example: "Is this safe?", "What are the regulations?", "Verify this claim"

### Use for Uncertain Situations
- **uncertainty-skill**: When input is incomplete or evidence is weak
  - Example: User asks vague question, conflicting data, missing information

### Use for Debugging
- **debugging-skill**: For bug reports, regressions, or unexpected behavior
  - Example: "This code doesn't work", "Tests are failing", "Why is this happening?"

### Use for Decisions
- **decision-tradeoff-skill**: When choosing between multiple options
  - Example: "Should I use React or Vue?", "Which architecture is better?"

### Use for Testing
- **test-design-skill**: When writing or reviewing tests
  - Example: "Write tests for this function", "Are these tests sufficient?"

## Usage Pattern

1. **Identify the task type** - Does it match a skill's purpose?
2. **Invoke the skill workflow** - Follow its steps exactly
3. **Apply the skill rules** - Respect constraints and guidelines
4. **Skills stack** - Multiple skills can be used together (e.g., retrieval-synthesis + mood)

## Example: Multi-Source Answer

User: "I'm going to Tokyo. Tell me weather, currency rates, and transport."

**Skills to use:**
1. **retrieval-synthesis-skill**: Combine weather + currency + transport data
2. **mood-skill**: Match user's casual tone

**Process:**
1. Gather data with tools (weather_lookup, currency, internet_search)
2. Use retrieval-synthesis-skill: normalize data, remove duplicates, preserve sources
3. Use mood-skill: detect casual tone ("I'm going to Tokyo")
4. Synthesize: "Hey! Tokyo's weather is 14°C with light rain. Dress in layers..."

## Objective

Skills ensure consistent, high-quality responses while keeping prompts token-efficient by loading detailed workflows only when needed.
