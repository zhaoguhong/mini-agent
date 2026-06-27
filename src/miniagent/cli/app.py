"""CLI entrypoint."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from miniagent.agent.factory import create_agent
from miniagent.config.loader import load_config
from miniagent.logging import configure_logging


def _load_typer():
    try:
        import typer
    except ModuleNotFoundError as exc:
        raise RuntimeError("The typer package is required. Install with `pip install -e .`.") from exc
    return typer


typer = _load_typer()
app = typer.Typer(no_args_is_help=False, add_completion=False)
config_app = typer.Typer(add_completion=False)
tools_app = typer.Typer(add_completion=False)
skills_app = typer.Typer(add_completion=False)
mcp_app = typer.Typer(add_completion=False)
memory_app = typer.Typer(add_completion=False)
app.add_typer(config_app, name="config")
app.add_typer(tools_app, name="tools")
app.add_typer(skills_app, name="skills")
app.add_typer(mcp_app, name="mcp")
app.add_typer(memory_app, name="memory")


def _agent_from_options(
    config: Optional[Path],
    api_key: Optional[str],
    base_url: Optional[str],
    model: Optional[str],
    stream: Optional[bool],
    workspace: Optional[Path],
):
    from miniagent.cli.output import Console

    console = Console()
    loaded = load_config(
        config_path=config,
        cli_overrides={
            "api_key": api_key,
            "base_url": base_url,
            "model": model,
            "stream": stream,
            "workspace_root": workspace,
        },
    )
    configure_logging(loaded.log_level)
    return create_agent(loaded, confirm=console.confirm), console


@app.callback(invoke_without_command=True)
def chat(
    ctx: typer.Context,
    config: Optional[Path] = typer.Option(None, "--config", help="Path to config TOML."),
    api_key: Optional[str] = typer.Option(None, "--api-key", help="API key. Prefer env var for real use."),
    base_url: Optional[str] = typer.Option(None, "--base-url", help="OpenAI-compatible base URL."),
    model: Optional[str] = typer.Option(None, "--model", help="Chat Completions model name."),
    stream: Optional[bool] = typer.Option(None, "--stream/--no-stream", help="Enable streaming output."),
    workspace: Optional[Path] = typer.Option(None, "--workspace", help="Workspace root."),
) -> None:
    """Start interactive chat when no subcommand is provided."""

    if ctx.invoked_subcommand is not None:
        return
    from miniagent.cli.repl import run_repl

    agent, console = _agent_from_options(config, api_key, base_url, model, stream, workspace)
    run_repl(agent, console)


@app.command()
def run(
    task: str,
    config: Optional[Path] = typer.Option(None, "--config"),
    api_key: Optional[str] = typer.Option(None, "--api-key"),
    base_url: Optional[str] = typer.Option(None, "--base-url"),
    model: Optional[str] = typer.Option(None, "--model"),
    stream: Optional[bool] = typer.Option(None, "--stream/--no-stream"),
    workspace: Optional[Path] = typer.Option(None, "--workspace"),
) -> None:
    """Run one task and exit."""

    agent, console = _agent_from_options(config, api_key, base_url, model, stream, workspace)
    text = agent.run(task, on_delta=console.write if agent.runtime.config.stream else None)
    if agent.runtime.config.stream:
        console.print("")
    else:
        console.print(text)


@config_app.command("show")
def config_show(config: Optional[Path] = typer.Option(None, "--config")) -> None:
    """Show effective config."""

    from miniagent.cli.output import Console

    console = Console()
    loaded = load_config(config_path=config)
    rows = [(key, str(value)) for key, value in loaded.__dict__.items() if key != "api_key"]
    console.table("Config", ["Key", "Value"], rows)


@tools_app.command("list")
def tools_list(config: Optional[Path] = typer.Option(None, "--config")) -> None:
    """List built-in tools without requiring an API key."""

    from miniagent.cli.output import Console
    from miniagent.skills.loader import SkillRepository
    from miniagent.tools import create_builtin_registry

    console = Console()
    loaded = load_config(config_path=config)
    repo = SkillRepository(loaded.skills_dir)
    repo.discover()
    registry = create_builtin_registry(repo)
    console.table("Tools", ["Name"], [(name,) for name in registry.names()])


@skills_app.command("list")
def skills_list(config: Optional[Path] = typer.Option(None, "--config")) -> None:
    """List discovered skills without loading full skill bodies."""

    from miniagent.cli.output import Console
    from miniagent.skills.loader import SkillRepository

    console = Console()
    loaded = load_config(config_path=config)
    repo = SkillRepository(loaded.skills_dir)
    repo.discover()
    console.table("Skills", ["Name", "Description"], [(item.name, item.description) for item in repo.index()])


@mcp_app.command("list")
def mcp_list(config: Optional[Path] = typer.Option(None, "--config")) -> None:
    """List configured MCP servers."""

    from miniagent.cli.output import Console

    console = Console()
    loaded = load_config(config_path=config)
    console.table("MCP Servers", ["Name", "Command"], [(server.name, server.command) for server in loaded.mcp_servers])


@memory_app.command("list")
def memory_list(config: Optional[Path] = typer.Option(None, "--config")) -> None:
    """List saved session files."""

    from miniagent.cli.output import Console

    console = Console()
    loaded = load_config(config_path=config)
    sessions = sorted(loaded.sessions_dir.glob("*.jsonl")) if loaded.sessions_dir.exists() else []
    console.table("Sessions", ["Session"], [(path.stem,) for path in sessions])


@memory_app.command("clear")
def memory_clear(config: Optional[Path] = typer.Option(None, "--config")) -> None:
    """Clear saved sessions and persistent memory files."""

    from miniagent.cli.output import Console

    console = Console()
    loaded = load_config(config_path=config)
    targets = []
    if loaded.sessions_dir.exists():
        targets.extend(path for path in loaded.sessions_dir.glob("*.jsonl") if path.is_file())
    if loaded.memory_dir.exists():
        targets.extend(path for path in loaded.memory_dir.glob("*.json") if path.is_file())
    for path in targets:
        path.unlink()
    console.print(f"Deleted {len(targets)} memory files.")


def main() -> None:
    app()
