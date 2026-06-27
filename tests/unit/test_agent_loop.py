import tempfile
import unittest
from pathlib import Path

from miniagent.agent.context import AgentRuntime
from miniagent.agent.loop import Agent
from miniagent.config.schema import AgentConfig
from miniagent.memory.session import SessionMemory
from miniagent.tools.registry import ToolRegistry
from miniagent.tools.base import ToolResult


class FakeLlm:
    def complete(self, messages, tools):
        return type("Response", (), {"message": {"role": "assistant", "content": "hello"}})()


class FakeToolLlm:
    def __init__(self):
        self.calls = 0

    def complete(self, messages, tools):
        self.calls += 1
        if self.calls == 1:
            return type(
                "Response",
                (),
                {
                    "message": {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [
                            {
                                "id": "call_1",
                                "type": "function",
                                "function": {"name": "echo", "arguments": '{"text": "hi"}'},
                            }
                        ],
                    }
                },
            )()
        return type("Response", (), {"message": {"role": "assistant", "content": "done"}})()


class EchoTool:
    name = "echo"
    description = "Echo text"
    parameters_schema = {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]}

    def run(self, arguments, context):
        return ToolResult(ok=True, content=arguments["text"])


class AgentLoopTests(unittest.TestCase):
    def test_agent_returns_final_text(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp_path = Path(raw)
            config = AgentConfig(api_key="key", model="model", workspace_root=tmp_path, stream=False)
            runtime = AgentRuntime(config=config, memory=SessionMemory(), tools=ToolRegistry())
            agent = Agent(runtime=runtime, llm_client=FakeLlm())

            result = agent.run("hi")

            self.assertEqual(result, "hello")
            self.assertEqual(runtime.memory.messages[-1]["content"], "hello")

    def test_agent_executes_tool_call(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp_path = Path(raw)
            config = AgentConfig(api_key="key", model="model", workspace_root=tmp_path, stream=False)
            registry = ToolRegistry()
            registry.register(EchoTool())
            runtime = AgentRuntime(config=config, memory=SessionMemory(), tools=registry)
            agent = Agent(runtime=runtime, llm_client=FakeToolLlm())

            result = agent.run("use echo")

            self.assertEqual(result, "done")
            self.assertEqual(runtime.memory.messages[-2]["role"], "tool")
            self.assertIn("OK: hi", runtime.memory.messages[-2]["content"])


if __name__ == "__main__":
    unittest.main()
