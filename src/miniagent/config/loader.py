"""Configuration loading and precedence handling."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

from miniagent.config.schema import AgentConfig, McpServerConfig


def _load_toml(path: Path) -> Dict[str, Any]:
    """Read a TOML file when it exists."""

    if not path.exists():
        return {}
    try:
        import tomllib  # type: ignore[attr-defined]
    except ModuleNotFoundError:
        import tomli as tomllib  # type: ignore[no-redef]
    with path.open("rb") as file:
        data = tomllib.load(file)
    if not isinstance(data, dict):
        return {}
    return data


def _bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _path(value: Any) -> Path:
    return Path(str(value)).expanduser()


def _env_values(env: Mapping[str, str]) -> Dict[str, Any]:
    """Translate supported environment variables into config field names."""

    mapping = {
        "MINIAGENT_API_KEY": "api_key",
        "MINIAGENT_MODEL": "model",
        "MINIAGENT_BASE_URL": "base_url",
        "MINIAGENT_DEFAULT_LANGUAGE": "default_language",
        "MINIAGENT_LOG_LEVEL": "log_level",
    }
    values: Dict[str, Any] = {}
    for env_name, field_name in mapping.items():
        if env_name in env:
            values[field_name] = env[env_name]

    bools = {
        "MINIAGENT_STREAM": "stream",
        "MINIAGENT_RENDER_MARKDOWN": "render_markdown",
        "MINIAGENT_SHELL_ENABLED": "shell_enabled",
        "MINIAGENT_REQUIRE_SHELL_CONFIRMATION": "require_shell_confirmation",
        "MINIAGENT_MCP_ENABLED": "mcp_enabled",
    }
    for env_name, field_name in bools.items():
        if env_name in env:
            values[field_name] = _bool(env[env_name])

    ints = {
        "MINIAGENT_MAX_ITERATIONS": "max_iterations",
        "MINIAGENT_TOOL_TIMEOUT": "tool_timeout",
        "MINIAGENT_SHELL_TIMEOUT": "shell_timeout",
        "MINIAGENT_MCP_TOOL_TIMEOUT": "mcp_tool_timeout",
    }
    for env_name, field_name in ints.items():
        if env_name in env:
            values[field_name] = int(env[env_name])

    floats = {"MINIAGENT_TEMPERATURE": "temperature"}
    for env_name, field_name in floats.items():
        if env_name in env:
            values[field_name] = float(env[env_name])

    paths = {
        "MINIAGENT_WORKSPACE": "workspace_root",
        "MINIAGENT_MEMORY_DIR": "memory_dir",
        "MINIAGENT_SESSIONS_DIR": "sessions_dir",
        "MINIAGENT_SKILLS_DIR": "skills_dir",
        "MINIAGENT_MCP_CONFIG": "mcp_config_path",
    }
    for env_name, field_name in paths.items():
        if env_name in env:
            values[field_name] = _path(env[env_name])
    return values


def _normalize_values(values: Dict[str, Any]) -> Dict[str, Any]:
    """Coerce raw config values into the types used by AgentConfig."""

    normalized = dict(values)
    for key in ["workspace_root", "memory_dir", "sessions_dir", "skills_dir", "mcp_config_path"]:
        if key in normalized and normalized[key] is not None:
            normalized[key] = _path(normalized[key])
    for key in [
        "stream",
        "render_markdown",
        "shell_enabled",
        "require_shell_confirmation",
        "file_write_confirmation",
        "mcp_enabled",
    ]:
        if key in normalized and normalized[key] is not None:
            normalized[key] = _bool(normalized[key])
    return normalized


def load_mcp_servers(path: Path) -> list[McpServerConfig]:
    """Load MCP server configs from a Claude-style JSON file."""

    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    servers = data.get("servers", {})
    loaded = []
    for name, raw in servers.items():
        if raw.get("transport", "stdio") != "stdio":
            continue
        loaded.append(
            McpServerConfig(
                name=name,
                transport=raw.get("transport", "stdio"),
                command=raw["command"],
                args=list(raw.get("args", [])),
                env=dict(raw.get("env", {})),
            )
        )
    return loaded


def load_config(
    config_path: Optional[Path] = None,
    cli_overrides: Optional[Dict[str, Any]] = None,
    env: Optional[Mapping[str, str]] = None,
) -> AgentConfig:
    """Load config with precedence: CLI > env > file > defaults."""

    active_env = env or os.environ
    path = config_path or Path.home() / ".miniagent" / "config.toml"
    file_values = _normalize_values(_load_toml(path.expanduser()))
    env_values = _env_values(active_env)
    cli_values = _normalize_values({k: v for k, v in (cli_overrides or {}).items() if v is not None})
    config = AgentConfig().with_updates(**file_values).with_updates(**env_values).with_updates(**cli_values)
    if config.mcp_enabled:
        config = config.with_updates(mcp_servers=load_mcp_servers(config.mcp_config_path))
    return config
