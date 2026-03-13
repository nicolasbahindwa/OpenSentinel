"""Tool for cleaning and formatting follow-up questions."""

from __future__ import annotations

import re
from typing import ClassVar, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field


def _normalize_question(text: str) -> str | None:
    cleaned = re.sub(r"^\s*(\d+[.)]|[-*])\s*", "", text).strip()
    if not cleaned:
        return None
    cleaned = re.sub(r"\s+", " ", cleaned)
    if not cleaned.endswith("?"):
        cleaned = cleaned.rstrip(".") + "?"
    # Preserve casing except for first character
    cleaned = cleaned[0].upper() + cleaned[1:] if cleaned else cleaned
    return cleaned


def clean_followups(questions: list[str], max_questions: int = 5) -> list[str]:
    seen: set[str] = set()
    cleaned: list[str] = []
    for q in questions:
        normalized = _normalize_question(q)
        if not normalized:
            continue
        key = normalized.lower()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(normalized)
        if len(cleaned) >= max_questions:
            break
    return cleaned


class FollowupWriterInput(BaseModel):
    questions: list[str] = Field(
        default_factory=list,
        description="Candidate follow-up questions to clean and format.",
    )
    max_questions: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Maximum number of follow-up questions to return.",
    )


class FollowupWriterTool(BaseTool):
    name: str = "followup_writer"
    description: str = (
        "Clean and format follow-up questions for display. "
        "Ensures consistent punctuation, spacing, and de-duplicates entries."
    )
    args_schema: Type[BaseModel] = FollowupWriterInput
    handle_tool_error: bool = True

    MAX_RESULTS: ClassVar[int] = 10

    def _run(self, questions: list[str], max_questions: int = 5) -> list[str]:
        max_questions = max(1, min(max_questions, self.MAX_RESULTS))
        return clean_followups(questions, max_questions=max_questions)

    async def _arun(self, questions: list[str], max_questions: int = 5) -> list[str]:
        return self._run(questions, max_questions)


__all__ = ["FollowupWriterTool", "clean_followups"]
