"""Production security guardrails middleware for OpenSentinel.

Implements defense-in-depth: input normalization, regex layers,
LLM judge classification, conversation analysis, rate-limit anomaly
detection, and response validation.
"""

from __future__ import annotations

import base64
import codecs
import hashlib
import re
import threading
import time
import unicodedata
from collections import defaultdict, deque
from typing import Any, ClassVar, Optional

from langchain.agents.middleware.types import (
    AgentMiddleware,
    AgentState,
    ContextT,
    ResponseT,
    hook_config,
)
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from typing_extensions import override

from agent.logger import get_logger

logger = get_logger("agent.middleware.guardrails", component="security")


# ============================================================================
# Input normalization (defeat obfuscation)
# ============================================================================


def _content_to_text(content: Any) -> str:
    """Normalize message content (string or content blocks) into plain text."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and isinstance(block.get("text"), str):
                parts.append(block["text"])
        return "\n".join(parts)
    return str(content)


def _normalize_text(text: str) -> str:
    """Normalize input to defeat common obfuscation techniques."""
    if not text:
        return ""
    # Remove zero-width characters
    text = re.sub(r"[\u200B\u200C\u200D\uFEFF]", "", text)
    # Normalize unicode homoglyphs to ASCII equivalents
    text = unicodedata.normalize("NFKC", text)
    # Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text.lower()


def _decode_common_encodings(text: str) -> list[str]:
    """Attempt to decode common obfuscation encodings."""
    variants = [text]

    # Base64 detection — minimum 3 groups (12 chars) to catch short payloads
    # like "cm0gLXJmIC8q" (rm -rf /*) while avoiding false positives on
    # normal words
    b64_pattern = re.compile(
        r"(?:[A-Za-z0-9+/]{4}){3,}(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?"
    )
    for match in b64_pattern.finditer(text):
        try:
            decoded = base64.b64decode(match.group()).decode("utf-8", errors="ignore")
            if decoded and decoded.isprintable():
                variants.append(decoded.lower())
        except Exception:
            pass

    # ROT13
    if re.search(r"\b[a-zA-Z]{4,}\b", text):
        rot13 = codecs.decode(text, "rot_13")
        if rot13 != text:
            variants.append(rot13.lower())

    return variants


# ============================================================================
# Threat detection
# ============================================================================


class ThreatDetector:
    """Multi-layer regex threat detection."""

    # Layer 0: Token injection — ChatML / special tokens (checked on RAW text)
    TOKEN_INJECTION: ClassVar[re.Pattern] = re.compile(
        r"<\|im_(end|start)\|>"
        r"|<\|system\|>|<\|user\|>|<\|assistant\|>"
        r"|<\|endoftext\|>|<\|begin_of_text\|>"
        r"|<\|eot_id\|>|<\|start_header_id\|>"
        r"|\[INST\]|\[/INST\]"
        r"|<<SYS>>|<</SYS>>",
        re.I,
    )

    # Layer 1: Hard-block — no educational override
    HARD_BLOCK: ClassVar[list[re.Pattern]] = [
        re.compile(
            r"\b(how\s+to|tutorial|guide|step[-\s]?by[-\s]?step|code\s+for)\b"
            r".{0,100}"
            r"\b(malware|ransomware|trojan|keylogger|rootkit|botnet)\b",
            re.I,
        ),
        re.compile(
            r"\b(build|assemble|construct|make)\b"
            r".{0,50}"
            r"\b(explosive|bomb|IED|improvised explosive)\b",
            re.I,
        ),
        re.compile(
            r"\b(automate|script|tool|program)\b"
            r".{0,30}"
            r"\b(steal\s+password|harvest\s+credential|phish|keylog)\b",
            re.I,
        ),
    ]

    # Layer 2: Contextual — blocked unless educational framing present
    CONTEXTUAL_PATTERNS: ClassVar[dict[str, re.Pattern]] = {
        "malware_discussion": re.compile(
            r"\b(malware|ransomware|trojan|exploit|vulnerability|zero[- ]?day)\b", re.I
        ),
        "weapon_discussion": re.compile(
            r"\b(bomb|explosive|weapon|firearm|ammunition)\b", re.I
        ),
        "credential_abuse": re.compile(
            r"\b(steal|crack|dump|brute[- ]?force)\b.{0,30}\b(password|credential|hash|token)\b",
            re.I,
        ),
        "unauthorized_access": re.compile(
            r"\b(bypass|circumvent|skip|disable|remove|break|get\s+around|get\s+past)\b"
            r".{0,50}"
            r"\b(authentication|authorization|login|firewall|security|2fa|mfa|access\s+control)\b",
            re.I,
        ),
    }

    # Educational phrases that allow contextual patterns to pass
    EDUCATIONAL_PHRASES: ClassVar[list[re.Pattern]] = [
        re.compile(
            r"\b(prevent|detect|mitigate|defend|protect|analyze|research|study|understand)\b",
            re.I,
        ),
        re.compile(
            r"\b(educational|academic|research|defensive|blue\s*team|awareness|compliance)\b",
            re.I,
        ),
        re.compile(
            r"\b(how\s+to\s+(prevent|detect|stop|protect\s+against|defend))\b", re.I
        ),
        re.compile(
            r"\b(history|historical|fiction|novel|movie|policy)\b", re.I
        ),
    ]

    def check_token_injection(self, raw_text: str) -> bool:
        """Check for ChatML/special token injection on RAW (un-normalized) text."""
        return bool(self.TOKEN_INJECTION.search(raw_text))

    def check_hard_block(self, text: str) -> bool:
        return any(p.search(text) for p in self.HARD_BLOCK)

    def check_contextual(self, text: str) -> tuple[str | None, bool]:
        """Returns (category, is_educational) or (None, False) if no match."""
        for category, pattern in self.CONTEXTUAL_PATTERNS.items():
            if pattern.search(text):
                is_edu = any(p.search(text) for p in self.EDUCATIONAL_PHRASES)
                return category, is_edu
        return None, False


# ============================================================================
# Conversation analysis (multi-turn attack detection)
# ============================================================================


class ConversationAnalyzer:
    """Track conversation patterns to detect jailbreak escalation."""

    def __init__(self, window_size: int = 10) -> None:
        self._history: dict[str, deque[str]] = defaultdict(
            lambda: deque(maxlen=window_size)
        )
        self._cumulative_risk: dict[str, float] = defaultdict(float)

    _OVERRIDE_RE = re.compile(
        r"\b(ignore\s+(previous|all|your|the|my)\s*(instructions|rules|guidelines|policies|restrictions|directives)"
        r"|disregard\s+(all\s+)?(instructions|rules|guidelines|policies|restrictions)"
        r"|forget\s+(everything|all|your|previous)"
        r"|new\s+instruction|you\s+are\s+now|act\s+as\s+if"
        r"|pretend\s+you\s+are|you\s+must\s+obey|override\s+(all|your|safety|content)"
        r"|no\s+(restrictions|limitations|rules|filters|policies)"
        r"|jailbreak|DAN\s+mode|do\s+anything\s+now"
        r"|system\s+override|admin\s+override)\b",
        re.I,
    )
    # ChatML / special token injection (model-level prompt boundary attack)
    _TOKEN_INJECTION_RE = re.compile(
        r"<\|im_(end|start)\|>"         # ChatML tokens
        r"|<\|system\|>"                 # system role token
        r"|<\|user\|>"                   # user role token
        r"|<\|assistant\|>"              # assistant role token
        r"|<\|endoftext\|>"              # GPT end-of-text
        r"|\[INST\]|\[/INST\]"          # Llama instruction tokens
        r"|<<SYS>>|<</SYS>>"            # Llama system tokens
        r"|<\|begin_of_text\|>"          # Llama 3 BOT
        r"|<\|eot_id\|>"                # Llama 3 end-of-turn
        r"|<\|start_header_id\|>",       # Llama 3 header
        re.I,
    )
    _SAFE_FRAMING_RE = re.compile(
        r"\b(novel|research|educational|hypothetical|fiction|story)\b", re.I
    )
    _ESCALATION_RE = re.compile(
        r"\b(malware|exploit|steal|bypass|hack|inject|payload)\b", re.I
    )

    def analyze(self, thread_id: str, text: str) -> dict[str, Any]:
        self._history[thread_id].append(text)
        history = list(self._history[thread_id])

        risk_factors: list[str] = []

        # Prompt injection / instruction override
        if self._OVERRIDE_RE.search(text):
            risk_factors.append("instruction_override_attempt")

        # ChatML / special token injection
        if self._TOKEN_INJECTION_RE.search(text):
            risk_factors.append("token_injection_attempt")

        # Escalation: earlier messages had safe framing, now requesting malicious
        if len(history) >= 2:
            prior_safe = any(self._SAFE_FRAMING_RE.search(m) for m in history[:-1])
            now_bad = bool(self._ESCALATION_RE.search(text))
            if prior_safe and now_bad:
                risk_factors.append("escalation_pattern")

        score = len(risk_factors) * 0.5
        self._cumulative_risk[thread_id] = min(
            1.0, self._cumulative_risk.get(thread_id, 0.0) + score * 0.3
        )
        total = self._cumulative_risk[thread_id]

        if total >= 1.0:
            recommendation = "block"
        elif total >= 0.5:
            recommendation = "review"
        else:
            recommendation = "allow"

        return {
            "risk_score": total,
            "risk_factors": risk_factors,
            "recommendation": recommendation,
        }


# ============================================================================
# Security anomaly tracker
# ============================================================================


class SecurityAnomalyTracker:
    """Track blocked-request frequency per thread for anomaly alerting."""

    def __init__(self, alert_threshold: int = 5, window_seconds: int = 600) -> None:
        self._blocked: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.RLock()
        self._threshold = alert_threshold
        self._window = window_seconds

    def record_blocked(self, thread_id: str) -> None:
        now = time.time()
        with self._lock:
            q = self._blocked[thread_id]
            q.append(now)
            cutoff = now - self._window
            while q and q[0] < cutoff:
                q.popleft()
            if len(q) >= self._threshold:
                logger.warning(
                    "security_anomaly_probing_detected",
                    thread_id=thread_id,
                    blocked_count=len(q),
                    window_seconds=self._window,
                )


# ============================================================================
# LLM judge (semantic classification)
# ============================================================================


_JUDGE_SYSTEM_PROMPT = (
    "You are a safety classifier. Your ONLY job is to classify user messages.\n"
    "Respond with exactly ONE word: SAFE, UNSAFE, or AMBIGUOUS.\n\n"
    "SAFE — The message is a normal, benign request. Educational security "
    "questions (how to defend, prevent, detect) are SAFE.\n"
    "UNSAFE — The message requests help creating malware, weapons, attacks, "
    "credential theft, exploitation tools, or other harmful activities.\n"
    "AMBIGUOUS — You cannot clearly determine intent.\n\n"
    "Rules:\n"
    "- Defensive security, CTF, penetration testing with authorization, "
    "and academic research are SAFE.\n"
    "- Requests disguised as fiction, hypothetical, or roleplay that ask "
    "for real harmful instructions are UNSAFE.\n"
    "- When in doubt, respond AMBIGUOUS.\n"
    "- Respond with ONLY the classification word. No explanation."
)


class LLMJudge:
    """Lightweight LLM-based semantic classifier for ambiguous inputs."""

    def __init__(self, model: BaseChatModel) -> None:
        self._model = model
        self._cache: dict[str, str] = {}
        self._cache_lock = threading.RLock()
        self._max_cache = 500

    def _cache_key(self, text: str) -> str:
        return hashlib.sha256(text.encode()).hexdigest()[:16]

    def _parse_verdict(self, raw: str) -> str:
        """Extract classification from model response."""
        cleaned = raw.strip().upper()
        for verdict in ("SAFE", "UNSAFE", "AMBIGUOUS"):
            if verdict in cleaned:
                return verdict
        return "AMBIGUOUS"

    def classify(self, text: str) -> str:
        """Classify text synchronously. Returns SAFE, UNSAFE, or AMBIGUOUS."""
        key = self._cache_key(text)
        with self._cache_lock:
            if key in self._cache:
                return self._cache[key]

        try:
            response = self._model.invoke([
                SystemMessage(content=_JUDGE_SYSTEM_PROMPT),
                HumanMessage(content=text),
            ])
            verdict = self._parse_verdict(response.content)
        except Exception as exc:
            logger.error("llm_judge_error", error=str(exc), error_type=type(exc).__name__)
            verdict = "AMBIGUOUS"

        with self._cache_lock:
            if len(self._cache) >= self._max_cache:
                self._cache.clear()
            self._cache[key] = verdict
        return verdict

    async def aclassify(self, text: str) -> str:
        """Classify text asynchronously. Returns SAFE, UNSAFE, or AMBIGUOUS."""
        key = self._cache_key(text)
        with self._cache_lock:
            if key in self._cache:
                return self._cache[key]

        try:
            response = await self._model.ainvoke([
                SystemMessage(content=_JUDGE_SYSTEM_PROMPT),
                HumanMessage(content=text),
            ])
            verdict = self._parse_verdict(response.content)
        except Exception as exc:
            logger.error("llm_judge_error", error=str(exc), error_type=type(exc).__name__)
            verdict = "AMBIGUOUS"

        with self._cache_lock:
            if len(self._cache) >= self._max_cache:
                self._cache.clear()
            self._cache[key] = verdict
        return verdict


# ============================================================================
# Main middleware
# ============================================================================

_REFUSAL = (
    "I can't assist with that request. "
    "If you're researching security topics, I can help with:\n"
    "- Defensive security practices\n"
    "- Vulnerability mitigation strategies\n"
    "- Security awareness and education\n"
    "- Ethical security research methodologies"
)

_ESCALATION_REFUSAL = (
    "I notice this conversation may be heading in an unsafe direction. "
    "Let's refocus on constructive, educational security topics."
)


class GuardrailsMiddleware(
    AgentMiddleware[AgentState[ResponseT], ContextT, ResponseT]
):
    """Production security guardrails with defense-in-depth.

    Layers:
    1. Input normalization (defeat obfuscation)
    2. Encoding decode (base64, ROT13)
    3. Hard-block regex (no educational override)
    4. Contextual regex + educational framing check
    5. LLM judge — semantic classification for ambiguous inputs (optional)
    6. Conversation history analysis (multi-turn jailbreak)
    7. Anomaly tracking (repeated blocked requests)
    8. Response validation (post-generation check)
    """

    def __init__(
        self,
        *,
        judge_model: Optional[BaseChatModel] = None,
        enable_response_validation: bool = True,
    ) -> None:
        super().__init__()
        self._detector = ThreatDetector()
        self._conversation = ConversationAnalyzer()
        self._anomaly = SecurityAnomalyTracker()
        self._judge = LLMJudge(judge_model) if judge_model else None
        self._validate_responses = enable_response_validation

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _thread_id(state: AgentState[ResponseT]) -> str:
        cfg = (state.get("config") or {}).get("configurable") or {}
        tid = cfg.get("thread_id")
        if tid:
            return str(tid)
        msgs = state.get("messages", [])
        raw = msgs[-1].content if msgs else ""
        return hashlib.sha256(str(raw).encode()).hexdigest()[:16]

    @staticmethod
    def _last_user_text(state: AgentState[ResponseT]) -> str:
        for msg in reversed(state.get("messages", [])):
            if isinstance(msg, HumanMessage):
                return _content_to_text(msg.content).strip()
        return ""

    @staticmethod
    def _input_hash(text: str) -> str:
        return hashlib.sha256(text.encode()).hexdigest()[:12]

    @staticmethod
    def _refusal(content: str) -> dict[str, Any]:
        return {"messages": [AIMessage(content=content)], "jump_to": "end"}

    # ------------------------------------------------------------------
    # Pre-model check
    # ------------------------------------------------------------------

    def _pre_check(
        self, state: AgentState[ResponseT]
    ) -> tuple[str, str, str, list[str]] | None:
        """Run regex layers. Returns (raw_text, tid, normalized, variants) or None if empty."""
        raw_text = self._last_user_text(state)
        if not raw_text:
            return None
        tid = self._thread_id(state)
        normalized = _normalize_text(raw_text)
        variants = _decode_common_encodings(normalized)
        return raw_text, tid, normalized, variants

    def _regex_check(
        self, raw_text: str, tid: str, variants: list[str]
    ) -> dict[str, Any] | str | None:
        """Run hard-block + contextual regex. Returns refusal dict, 'judge', or None."""
        # Layer 0: Token injection (on raw text, before normalization strips markers)
        if self._detector.check_token_injection(raw_text):
            self._anomaly.record_blocked(tid)
            logger.warning(
                "security_token_injection_block",
                thread_id=tid,
                input_hash=self._input_hash(raw_text),
            )
            return self._refusal(_REFUSAL)

        # Layer 1-2: Hard-block (all text variants)
        for variant in variants:
            if self._detector.check_hard_block(variant):
                self._anomaly.record_blocked(tid)
                logger.warning(
                    "security_hard_block",
                    thread_id=tid,
                    input_hash=self._input_hash(raw_text),
                )
                return self._refusal(_REFUSAL)

        # Layer 3: Contextual + educational framing
        for variant in variants:
            category, is_edu = self._detector.check_contextual(variant)
            if category is not None:
                if is_edu:
                    logger.info(
                        "security_educational_allowed",
                        thread_id=tid,
                        category=category,
                        input_hash=self._input_hash(raw_text),
                    )
                elif self._judge:
                    # Ambiguous — defer to LLM judge
                    return "judge"
                else:
                    self._anomaly.record_blocked(tid)
                    logger.warning(
                        "security_contextual_block",
                        thread_id=tid,
                        category=category,
                        input_hash=self._input_hash(raw_text),
                    )
                    return self._refusal(_REFUSAL)

        return None

    def _handle_judge_verdict(
        self, verdict: str, raw_text: str, tid: str
    ) -> dict[str, Any] | None:
        """Act on the LLM judge classification."""
        if verdict == "SAFE":
            logger.info(
                "security_judge_allowed",
                thread_id=tid,
                verdict=verdict,
                input_hash=self._input_hash(raw_text),
            )
            return None
        elif verdict == "UNSAFE":
            self._anomaly.record_blocked(tid)
            logger.warning(
                "security_judge_blocked",
                thread_id=tid,
                verdict=verdict,
                input_hash=self._input_hash(raw_text),
            )
            return self._refusal(_REFUSAL)
        else:
            # AMBIGUOUS — fail-closed
            self._anomaly.record_blocked(tid)
            logger.warning(
                "security_judge_ambiguous_block",
                thread_id=tid,
                verdict=verdict,
                input_hash=self._input_hash(raw_text),
            )
            return self._refusal(_REFUSAL)

    def _conversation_check(
        self, raw_text: str, tid: str, normalized: str
    ) -> dict[str, Any] | None:
        """Layer 5: Multi-turn conversation analysis."""
        assessment = self._conversation.analyze(tid, normalized)
        if assessment["recommendation"] == "block":
            self._anomaly.record_blocked(tid)
            logger.warning(
                "security_conversation_block",
                thread_id=tid,
                risk_score=assessment["risk_score"],
                risk_factors=assessment["risk_factors"],
                input_hash=self._input_hash(raw_text),
            )
            return self._refusal(_ESCALATION_REFUSAL)
        return None

    def _check(self, state: AgentState[ResponseT]) -> dict[str, Any] | None:
        pre = self._pre_check(state)
        if pre is None:
            return None
        raw_text, tid, normalized, variants = pre

        # Regex layers
        result = self._regex_check(raw_text, tid, variants)
        if isinstance(result, dict):
            return result
        if result == "judge":
            verdict = self._judge.classify(normalized)  # type: ignore[union-attr]
            judge_result = self._handle_judge_verdict(verdict, raw_text, tid)
            if judge_result is not None:
                return judge_result

        # Multi-turn analysis
        return self._conversation_check(raw_text, tid, normalized)

    async def _acheck(self, state: AgentState[ResponseT]) -> dict[str, Any] | None:
        pre = self._pre_check(state)
        if pre is None:
            return None
        raw_text, tid, normalized, variants = pre

        # Regex layers
        result = self._regex_check(raw_text, tid, variants)
        if isinstance(result, dict):
            return result
        if result == "judge":
            verdict = await self._judge.aclassify(normalized)  # type: ignore[union-attr]
            judge_result = self._handle_judge_verdict(verdict, raw_text, tid)
            if judge_result is not None:
                return judge_result

        # Multi-turn analysis
        return self._conversation_check(raw_text, tid, normalized)

    @hook_config(can_jump_to=["end"])
    @override
    def before_model(
        self,
        state: AgentState[ResponseT],
        runtime: Any,
    ) -> dict[str, Any] | None:
        return self._check(state)

    async def abefore_model(
        self,
        state: AgentState[ResponseT],
        runtime: Any,
    ) -> dict[str, Any] | None:
        return await self._acheck(state)

    # ------------------------------------------------------------------
    # Post-model response validation
    # ------------------------------------------------------------------

    def _validate_response(self, state: AgentState[ResponseT]) -> dict[str, Any] | None:
        if not self._validate_responses:
            return None
        messages = state.get("messages", [])
        if not messages:
            return None
        last = messages[-1]
        if not isinstance(last, AIMessage):
            return None

        text = _normalize_text(_content_to_text(last.content))
        if self._detector.check_hard_block(text):
            tid = self._thread_id(state)
            logger.error(
                "security_response_violation",
                thread_id=tid,
                response_hash=self._input_hash(text),
            )
            return self._refusal(_REFUSAL)
        return None

    @override
    def after_model(
        self,
        state: AgentState[ResponseT],
        runtime: Any,
    ) -> dict[str, Any] | None:
        return self._validate_response(state)

    async def aafter_model(
        self,
        state: AgentState[ResponseT],
        runtime: Any,
    ) -> dict[str, Any] | None:
        return self._validate_response(state)


__all__ = ["GuardrailsMiddleware"]
