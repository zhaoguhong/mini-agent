"""Slash command handling."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from miniagent.agent.loop import Agent


@dataclass
class CommandResult:
    handled: bool
    exit_requested: bool = False


def handle_slash_command(text: str, agent: Agent, console) -> CommandResult:
    """Handle one slash command in the REPL."""

    parts = text.strip().split()
    command = parts[0] if parts else ""
    args = parts[1:]
    if command in {"/exit", "/quit"}:
        return CommandResult(handled=True, exit_requested=True)
    if command == "/help":
        console.print("/help /exit /clear /model /model <name> /config /tools /skills /mcp /memory /save /new /stream on|off")
        return CommandResult(handled=True)
    if command == "/clear":
        agent.runtime.memory.clear()
        console.print("Session cleared.")
        return CommandResult(handled=True)
    if command == "/new":
        agent.runtime.memory.clear()
        console.print("Started a new session.")
        return CommandResult(handled=True)
    if command == "/model":
        if args:
            agent.runtime.config = agent.runtime.config.with_updates(model=args[0])
        console.print(f"Model: {agent.runtime.config.model}")
        return CommandResult(handled=True)
    if command == "/stream":
        if args and args[0] in {"on", "off"}:
            agent.runtime.config = agent.runtime.config.with_updates(stream=args[0] == "on")
        console.print(f"Stream: {agent.runtime.config.stream}")
        return CommandResult(handled=True)
    if command == "/config":
        config = agent.runtime.config
        rows = [
            ("model", config.model or ""),
            ("base_url", config.base_url or "OpenAI default"),
            ("stream", str(config.stream)),
            ("workspace_root", str(config.workspace_root)),
            ("skills_dir", str(config.skills_dir)),
            ("mcp_enabled", str(config.mcp_enabled)),
        ]
        console.table("Config", ["Key", "Value"], rows)
        return CommandResult(handled=True)
    if command == "/tools":
        console.table("Tools", ["Name"], [(name,) for name in agent.runtime.tools.names()])
        return CommandResult(handled=True)
    if command == "/skills":
        repo = agent.skill_repository
        rows = [] if repo is None else [(item.name, item.description) for item in repo.index()]
        console.table("Skills", ["Name", "Description"], rows)
        return CommandResult(handled=True)
    if command == "/mcp":
        rows = [(server.name, server.command) for server in agent.runtime.config.mcp_servers]
        console.table("MCP Servers", ["Name", "Command"], rows)
        return CommandResult(handled=True)
    if command == "/memory":
        console.print(f"Session messages: {len(agent.runtime.memory.messages)}")
        return CommandResult(handled=True)
    if command == "/save":
        from miniagent.memory.store import SessionStore

        session_id = SessionStore(agent.runtime.config.sessions_dir).save(agent.runtime.memory.snapshot())
        console.print(f"Saved session: {session_id}")
        return CommandResult(handled=True)
    if command.startswith("/"):
        console.print("Unknown command. Use /help.")
        return CommandResult(handled=True)
    return CommandResult(handled=False)
