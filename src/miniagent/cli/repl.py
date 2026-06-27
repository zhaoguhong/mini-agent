"""Interactive REPL."""

from __future__ import annotations

from miniagent.agent.loop import Agent
from miniagent.cli.commands import handle_slash_command


def run_repl(agent: Agent, console) -> None:
    """Run an interactive miniagent session."""

    console.print("miniagent interactive session. Type /help for commands.")
    while True:
        try:
            text = input("You > ")
        except (EOFError, KeyboardInterrupt):
            console.print("")
            return
        if not text.strip():
            continue
        if text.startswith("/"):
            result = handle_slash_command(text, agent, console)
            if result.exit_requested:
                return
            if result.handled:
                continue
        try:
            agent.run(text, on_delta=console.write if agent.runtime.config.stream else None)
            if agent.runtime.config.stream:
                console.print("")
        except Exception as exc:
            console.print(f"Error: {exc}")

