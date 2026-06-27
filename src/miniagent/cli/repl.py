"""Interactive REPL."""

from __future__ import annotations

from miniagent.agent.loop import Agent
from miniagent.cli.commands import handle_slash_command


def run_repl(agent: Agent, console) -> None:
    """Run an interactive miniagent session."""

    console.intro()
    while True:
        try:
            text = console.input("You")
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
            if agent.runtime.config.stream:
                with console.markdown_stream(agent.runtime.config.render_markdown) as stream:
                    agent.run(text, on_delta=stream.write)
            else:
                answer = agent.run(text)
                console.render_assistant(answer, agent.runtime.config.render_markdown)
        except Exception as exc:
            console.print(f"Error: {exc}")
