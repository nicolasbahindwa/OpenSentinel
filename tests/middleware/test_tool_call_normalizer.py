from __future__ import annotations

from types import SimpleNamespace

import pytest
from langchain.agents.middleware.types import ModelResponse
from langchain_core.messages import AIMessage

from agent.middleware.tool_call_normalizer import ToolCallNormalizerMiddleware


def _request() -> SimpleNamespace:
    return SimpleNamespace(
        tools=[
            SimpleNamespace(name="web_browser"),
            SimpleNamespace(name="weather_lookup"),
            SimpleNamespace(name="currency"),
        ]
    )


def _response(content: str) -> ModelResponse[None]:
    return ModelResponse(
        result=[AIMessage(content=content, name="tester")],
        structured_response=None,
    )


def test_wrap_model_call_normalizes_fetch_json() -> None:
    middleware = ToolCallNormalizerMiddleware()

    result = middleware.wrap_model_call(_request(), lambda _req: _response(
        '{"type":"function","name":"fetch","parameters":{"url":"https://example.com"}}'
    ))

    assert isinstance(result, ModelResponse)
    message = result.result[-1]
    assert isinstance(message, AIMessage)
    assert message.tool_calls
    assert message.tool_calls[0]["name"] == "web_browser"
    assert message.tool_calls[0]["args"] == {
        "action": "fetch",
        "url": "https://example.com",
    }


@pytest.mark.asyncio
async def test_awrap_model_call_normalizes_fetch_page_json() -> None:
    middleware = ToolCallNormalizerMiddleware()

    async def handler(_req: SimpleNamespace) -> ModelResponse[None]:
        return _response(
            '{"type":"function","name":"fetch_page","parameters":{"url":"https://example.com/page"}}'
        )

    result = await middleware.awrap_model_call(_request(), handler)

    assert isinstance(result, ModelResponse)
    message = result.result[-1]
    assert isinstance(message, AIMessage)
    assert message.tool_calls
    assert message.tool_calls[0]["name"] == "web_browser"
    assert message.tool_calls[0]["args"] == {
        "action": "fetch",
        "url": "https://example.com/page",
    }


def test_wrap_model_call_normalizes_json_tool_list() -> None:
    middleware = ToolCallNormalizerMiddleware()

    result = middleware.wrap_model_call(_request(), lambda _req: _response(
        '[{"type":"function","name":"weather_lookup","parameters":{"location":"Tokyo","units":"metric"}},'
        '{"type":"function","name":"currency","parameters":{"action":"convert","base":"USD","target":"JPY","amount":"1"}}]'
    ))

    assert isinstance(result, ModelResponse)
    message = result.result[-1]
    assert isinstance(message, AIMessage)
    assert message.tool_calls
    assert message.tool_calls[0]["name"] == "weather_lookup"
    assert message.tool_calls[0]["args"] == {
        "location": "Tokyo",
        "units": "metric",
    }
