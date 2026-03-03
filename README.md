Backend
Add a persistent DB-backed store (Postgres/Redis) instead of only in-memory state.
Separate namespaces per user/session/tenant to avoid data mixing.
Add retention/TTL and cleanup policies for /memories/ and /workspace/.
Add audit/event storage for tool/subagent actions.
Middleware
Add guardrails middleware:
PII redaction
prompt-injection filtering
tool allow/deny policy by role
Add observability middleware:
structured logs
latency/error metrics per tool/subagent
Add rate-limit and retry policy middleware for external APIs.
Add routing middleware rules for when to force subagent delegation.
State
Define a typed state schema (what fields exist, required/optional).
Add state validation at step boundaries.
Add checkpoint/recovery strategy for long runs.
Add versioning/migrations for state shape changes over time.
Practical order:

Persistence + tenant isolation
Observability + retries/rate-limits
Guardrails + typed state validation
Checkpointing/versioned state migrations