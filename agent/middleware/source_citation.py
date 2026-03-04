import re
from typing import Awaitable, Callable

from langchain.agents.middleware.types import AgentMiddleware, ModelRequest, ModelResponse
from langchain_core.messages import AIMessage, SystemMessage


class SourceCitationMiddleware(AgentMiddleware):
    """Enforces source citation in factual responses.

    Checks model responses for source citations. If a response appears to contain
    factual claims but no sources, injects a correction prompt and retries once.
    """

    MIN_FACTUAL_LENGTH = 120

    _CITATION_PATTERNS = [
        re.compile(r"https?://\S+"),
        re.compile(r"\[.+?\]\(https?://\S+?\)"),
        re.compile(r"Sources?\s*:", re.IGNORECASE),
    ]

    _CONVERSATIONAL_PATTERNS = [
        re.compile(
            r"^(hi|hello|hey|greetings|good\s+(morning|afternoon|evening))",
            re.IGNORECASE,
        ),
        re.compile(
            r"^(thanks|thank you|you're welcome|no problem|sure|ok|okay)",
            re.IGNORECASE,
        ),
        re.compile(r"^(I'm sorry|apologies|unfortunately)", re.IGNORECASE),
    ]

    _CODE_HEAVY_PATTERN = re.compile(r"```[\s\S]{50,}```")

    _NUDGE = (
        "\n\n[IMPORTANT: Your previous response contained factual claims without "
        "source citations. You MUST use internet_search to verify your claims and "
        "include source URLs. Rewrite your response with proper inline citations. "
        "If you cannot verify a claim, explicitly state that it is unverified.]"
    )

    _DISCLAIMER = (
        "\n\n---\n*Note: Some information in this response could not be independently "
        "verified with current sources. Please verify critical claims independently.*"
    )

    # ------------------------------------------------------------------ helpers

    def _has_citations(self, text: str) -> bool:
        return any(p.search(text) for p in self._CITATION_PATTERNS)

    def _is_conversational(self, text: str) -> bool:
        if len(text) < self.MIN_FACTUAL_LENGTH:
            return True
        return any(p.match(text.strip()) for p in self._CONVERSATIONAL_PATTERNS)

    def _is_code_heavy(self, text: str) -> bool:
        code_matches = self._CODE_HEAVY_PATTERN.findall(text)
        code_length = sum(len(m) for m in code_matches)
        return code_length > len(text) * 0.5

    @staticmethod
    def _has_tool_calls(response: ModelResponse) -> bool:
        for msg in response.result:
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                return True
        return False

    def _needs_citation_check(self, response: ModelResponse) -> bool:
        if self._has_tool_calls(response):
            return False
        for msg in response.result:
            if isinstance(msg, AIMessage) and msg.content:
                text = msg.content if isinstance(msg.content, str) else str(msg.content)
                if self._is_conversational(text):
                    return False
                if self._is_code_heavy(text):
                    return False
                if not self._has_citations(text):
                    return True
        return False

    def _inject_nudge(self, request: ModelRequest) -> ModelRequest:
        existing = request.system_message.text if request.system_message else ""
        if self._NUDGE in existing:
            return request
        merged = f"{existing}{self._NUDGE}"
        return request.override(system_message=SystemMessage(content=merged))

    def _append_disclaimer(self, response: ModelResponse) -> ModelResponse:
        new_results = []
        for msg in response.result:
            if isinstance(msg, AIMessage) and msg.content:
                text = msg.content if isinstance(msg.content, str) else str(msg.content)
                new_results.append(AIMessage(content=text + self._DISCLAIMER))
            else:
                new_results.append(msg)
        return ModelResponse(
            result=new_results,
            structured_response=response.structured_response,
        )

    # ----------------------------------------------------------- middleware hooks

    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        response = handler(request)

        if not self._needs_citation_check(response):
            return response

        retry_response = handler(self._inject_nudge(request))

        if self._needs_citation_check(retry_response):
            return self._append_disclaimer(retry_response)

        return retry_response

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelResponse:
        response = await handler(request)

        if not self._needs_citation_check(response):
            return response

        retry_response = await handler(self._inject_nudge(request))

        if self._needs_citation_check(retry_response):
            return self._append_disclaimer(retry_response)

        return retry_response
