"""Factory helpers for building an agent session."""

from __future__ import annotations

from typing import Any, Callable, Optional

from miniagent.agent.context import AgentRuntime
from miniagent.agent.loop import Agent
from miniagent.config.schema import AgentConfig
from miniagent.llm.client import OpenAIChatClient
from miniagent.mcp.adapter import load_mcp_tools
from miniagent.mcp.client import McpClient
from miniagent.memory.session import SessionMemory
from miniagent.skills.loader import SkillRepository
from miniagent.tools import create_builtin_registry


def create_agent(config: AgentConfig, confirm: Optional[Callable[[str], bool]] = None) -> Agent:
    """Build a configured agent with built-in tools, skills, and optional MCP tools."""

    config.validate_required()
    skills = SkillRepository(config.skills_dir)
    skills.discover()
    registry = create_builtin_registry(skills)
    if config.mcp_enabled and config.mcp_servers:
        mcp_client = McpClient(config.mcp_servers)
        registry.extend(load_mcp_tools(mcp_client))
    extras: dict[str, Any] = {}
    if confirm is not None:
        extras["confirm"] = confirm
    runtime = AgentRuntime(config=config, memory=SessionMemory(), tools=registry, extras=extras)
    return Agent(runtime=runtime, llm_client=OpenAIChatClient(config), skill_repository=skills)
