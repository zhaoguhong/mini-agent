"""OpenAI SDK wrapper for Chat Completions."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

from miniagent.config.schema import AgentConfig
from miniagent.llm.protocol import ChatResponse, StreamDelta


class OpenAIChatClient:
    """Small wrapper around OpenAI's Chat Completions API."""

    def __init__(self, config: AgentConfig) -> None:
        try:
            from openai import OpenAI
        except ModuleNotFoundError as exc:
            raise RuntimeError("The openai package is required. Install with `pip install -e .`.") from exc
        kwargs: Dict[str, Any] = {"api_key": config.api_key}
        if config.base_url:
            kwargs["base_url"] = config.base_url
        self._client = OpenAI(**kwargs)
        self._config = config

    def complete(self, messages: List[Dict[str, Any]], tools: List[Dict[str, Any]]) -> ChatResponse:
        """Create one non-streaming Chat Completions response."""

        kwargs: Dict[str, Any] = {
            "model": self._config.model,
            "messages": messages,
            "temperature": self._config.temperature,
            "stream": False,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"
        response = self._client.chat.completions.create(**kwargs)
        message = response.choices[0].message
        return ChatResponse(message=_message_to_dict(message))

    def stream(self, messages: List[Dict[str, Any]], tools: List[Dict[str, Any]]) -> Iterable[StreamDelta]:
        """Yield normalized streaming deltas from Chat Completions."""

        kwargs: Dict[str, Any] = {
            "model": self._config.model,
            "messages": messages,
            "temperature": self._config.temperature,
            "stream": True,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"
        stream = self._client.chat.completions.create(**kwargs)
        for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            yield StreamDelta(content=getattr(delta, "content", "") or "", tool_calls=_tool_calls_to_dicts(getattr(delta, "tool_calls", None)))


def _message_to_dict(message: Any) -> Dict[str, Any]:
    """Convert SDK message objects into plain dictionaries for the agent."""

    if isinstance(message, dict):
        return message
    result: Dict[str, Any] = {"role": getattr(message, "role", "assistant")}
    content = getattr(message, "content", None)
    if content is not None:
        result["content"] = content
    tool_calls = _tool_calls_to_dicts(getattr(message, "tool_calls", None))
    if tool_calls:
        result["tool_calls"] = tool_calls
    return result


def _tool_calls_to_dicts(tool_calls: Any) -> Optional[List[Dict[str, Any]]]:
    """Convert SDK tool-call objects into Chat Completions dictionaries."""

    if not tool_calls:
        return None
    converted = []
    for call in tool_calls:
        if isinstance(call, dict):
            converted.append(call)
            continue
        function = getattr(call, "function", None)
        converted.append(
            {
                "id": getattr(call, "id", None),
                "type": getattr(call, "type", "function"),
                "index": getattr(call, "index", None),
                "function": {
                    "name": getattr(function, "name", None) if function else None,
                    "arguments": getattr(function, "arguments", "") if function else "",
                },
            }
        )
    return converted
