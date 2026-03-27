---
name: verification-skill
description: Verify factual claims, detect unsupported assertions, and separate evidence from inference before answering high-stakes or uncertain questions
---

# Verification Skill

Use this skill when the answer could be wrong in a costly way or when evidence quality matters.

## Trigger

- Factual claims with real-world consequences
- Conflicting evidence
- User asks to verify, fact-check, confirm, or check sources
- Medical, legal, financial, regulatory, or current-events topics

## Workflow

1. List the core claims that need verification.
2. Mark each as one of: verified, partially supported, unsupported, or unclear.
3. Prefer primary sources and direct evidence.
4. Separate observed facts, inference, and uncertainty.
5. If evidence is weak, say so explicitly instead of smoothing it over.

## Output Rules

- Lead with the answer or verdict.
- Include only the evidence needed to justify it.
- Do not present inferences as facts.
- When evidence is mixed, explain the conflict briefly.

End of Skill.
