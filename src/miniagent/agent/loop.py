"""Core agent loop."""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from typing import Any, Callable, Dict, List, Optional

from miniagent.agent.context import AgentRuntime
from miniagent.llm.protocol import ChatResponse, StreamDelta
from miniagent.memory.persistent import PersistentMemory
from miniagent.skills.loader import SkillRepository
from miniagent.tools.base import ToolContext

StreamCallback = Callable[[str], None]


class Agent:
    """A minimal but complete Chat Completions agent loop.

    The loop owns orchestration only: it builds messages, asks the model for the
    next step, executes requested tools, and feeds tool results back to the
    model. Tool implementations, persistence, and provider details stay behind
    their own interfaces so the learning surface remains small.
    """

    def __init__(
        self,
        runtime: AgentRuntime,
        llm_client: Any,
        skill_repository: Optional[SkillRepository] = None,
    ) -> None:
        self.runtime = runtime
        self.llm = llm_client
        self.skill_repository = skill_repository

    def run(self, user_input: str, on_delta: Optional[StreamCallback] = None) -> str:
        """Run one user turn until a final assistant message is produced.

        A turn may require multiple model calls when the assistant requests
        tools. Each assistant tool-call message and each tool result is appended
        to both the temporary request context and session memory so later turns
        can see the same reasoning trail.
        """

        self.runtime.memory.add({"role": "user", "content": user_input})
        messages = self._build_messages()
        final_text = ""

        for _ in range(self.runtime.config.max_iterations):
            response = self._call_llm(messages, on_delta)
            message = response.message
            tool_calls = message.get("tool_calls") or []
            if not tool_calls:
                final_text = message.get("content", "") or ""
                if not self.runtime.config.stream or not on_delta:
                    if final_text:
                        on_delta and on_delta(final_text)
                self.runtime.memory.add({"role": "assistant", "content": final_text})
                return final_text

            messages.append(_assistant_tool_message(message))
            self.runtime.memory.add(_assistant_tool_message(message))
            for call in tool_calls:
                tool_message = self._execute_tool_call(call)
                messages.append(tool_message)
                self.runtime.memory.add(tool_message)

        final_text = "Reached max agent iterations before a final answer."
        self.runtime.memory.add({"role": "assistant", "content": final_text})
        return final_text

    def _build_messages(self) -> List[Dict[str, Any]]:
        """Build the model-visible context for the current turn.

        Skills use progressive disclosure: only the minimal skill index is
        injected here. The model must call `load_skill` before the longer skill
        instructions or reference files enter the context.
        """

        system_parts = [_default_system_prompt(), _language_instruction(self.runtime.config.default_language)]
        persistent = PersistentMemory(self.runtime.config.memory_dir).load_summary()
        if persistent:
            system_parts.append("Persistent memory:\n" + persistent)
        if self.skill_repository:
            index = self.skill_repository.index()
            if index:
                lines = ["Available skills. Use load_skill when one is relevant:"]
                for item in index:
                    lines.append(f"- {item.name}: {item.description}")
                system_parts.append("\n".join(lines))
        return [{"role": "system", "content": "\n\n".join(system_parts)}] + self.runtime.memory.snapshot()

    def _call_llm(self, messages: List[Dict[str, Any]], on_delta: Optional[StreamCallback]) -> ChatResponse:
        """Dispatch to streaming or non-streaming Chat Completions."""

        tools = self.runtime.tools.schemas()
        if not self.runtime.config.stream:
            return self.llm.complete(messages, tools)
        return self._collect_stream(messages, tools, on_delta)

    def _collect_stream(self, messages: List[Dict[str, Any]], tools: List[Dict[str, Any]], on_delta: Optional[StreamCallback]) -> ChatResponse:
        """Normalize streaming deltas into a single assistant message.

        Chat Completions streams text and tool-call arguments as partial deltas.
        The agent can display text immediately, but tool calls must be rebuilt
        into one complete assistant message before JSON arguments can be parsed
        and executed safely.
        """

        content_parts: List[str] = []
        tool_calls: Dict[int, Dict[str, Any]] = {}
        for delta in self.llm.stream(messages, tools):
            if isinstance(delta, dict):
                delta = StreamDelta(content=delta.get("content", ""), tool_calls=delta.get("tool_calls"))
            if delta.content:
                content_parts.append(delta.content)
                if on_delta:
                    on_delta(delta.content)
            for call in delta.tool_calls or []:
                index = int(call.get("index") or 0)
                existing = tool_calls.setdefault(index, {"id": call.get("id"), "type": "function", "function": {"name": "", "arguments": ""}})
                if call.get("id"):
                    existing["id"] = call.get("id")
                function = call.get("function") or {}
                # Streaming tool calls arrive in fragments, so name and arguments
                # are appended until the final assistant message can be rebuilt.
                if function.get("name"):
                    existing["function"]["name"] += function.get("name") or ""
                if function.get("arguments"):
                    existing["function"]["arguments"] += function.get("arguments") or ""
        message: Dict[str, Any] = {"role": "assistant", "content": "".join(content_parts)}
        if tool_calls:
            message["tool_calls"] = [tool_calls[index] for index in sorted(tool_calls)]
        return ChatResponse(message=message)

    def _execute_tool_call(self, call: Dict[str, Any]) -> Dict[str, Any]:
        """Execute one Chat Completions tool call and return a tool message."""

        function = call.get("function") or {}
        name = function.get("name")
        raw_args = function.get("arguments") or "{}"
        try:
            arguments = json.loads(raw_args)
        except json.JSONDecodeError as exc:
            content = f"ERROR: Invalid tool arguments JSON: {exc}"
            return {"role": "tool", "tool_call_id": call.get("id"), "content": content}

        try:
            tool = self.runtime.tools.get(name)
            timeout = self._tool_timeout(name)
            result = self._run_tool_with_timeout(tool, arguments, timeout)
        except Exception as exc:
            content = f"ERROR: {exc}"
        else:
            content = result.to_message_content(self.runtime.config.max_tool_output_chars)
        return {"role": "tool", "tool_call_id": call.get("id"), "content": content}

    def _run_tool_with_timeout(self, tool: Any, arguments: Dict[str, Any], timeout: int):
        """Run synchronous tools behind a timeout without changing the Tool API.

        Tools are intentionally simple synchronous callables. The agent wraps
        them in a worker thread to enforce per-tool timeouts while keeping the
        public Tool interface easy to implement and test.
        """

        context = ToolContext(config=self.runtime.config, extras=self.runtime.extras)
        executor = ThreadPoolExecutor(max_workers=1)
        future = executor.submit(tool.run, arguments, context)
        try:
            return future.result(timeout=timeout)
        except TimeoutError:
            future.cancel()
            raise TimeoutError(f"Tool timed out after {timeout}s")
        finally:
            executor.shutdown(wait=False, cancel_futures=True)

    def _tool_timeout(self, name: str) -> int:
        """Pick the timeout policy for built-in, shell, and MCP tools.

        Shell commands enforce their own subprocess timeout, so the outer agent
        timeout is slightly larger to let the shell tool return a structured
        timeout error instead of being interrupted first.
        """

        if name == "run_shell":
            return self.runtime.config.shell_timeout + 1
        if name.startswith("mcp__"):
            return self.runtime.config.mcp_tool_timeout
        return self.runtime.config.tool_timeout


def _assistant_tool_message(message: Dict[str, Any]) -> Dict[str, Any]:
    """Preserve assistant tool-call messages in Chat Completions format."""

    result = {"role": "assistant", "content": message.get("content")}
    if message.get("tool_calls"):
        result["tool_calls"] = message["tool_calls"]
    return result


def _default_system_prompt() -> str:
    return (
        "You are mini-agent, a command-line learning agent. "
        "Use tools when they help. Keep file and shell actions scoped to the workspace. "
        "If a skill looks relevant, call load_skill before applying it."
    )


def _language_instruction(language: str) -> str:
    """Build the default response language instruction for the model."""

    return (
        f"Default response language: {language}. "
        "Follow the user's explicit language request when present. "
        "Keep code, commands, file paths, identifiers, and quoted tool output unchanged unless translation is requested."
    )
