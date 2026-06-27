"""Configuration models for mini-agent."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class McpServerConfig:
    """Configuration for one MCP server."""

    name: str
    transport: str
    command: str
    args: List[str] = field(default_factory=list)
    env: Dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class AgentConfig:
    """Runtime configuration for the agent."""

    api_key: Optional[str] = None
    model: Optional[str] = None
    base_url: Optional[str] = None
    stream: bool = True
    temperature: float = 0.2
    max_iterations: int = 8
    workspace_root: Path = field(default_factory=Path.cwd)
    memory_dir: Path = field(default_factory=lambda: Path.home() / ".miniagent" / "memory")
    sessions_dir: Path = field(default_factory=lambda: Path.home() / ".miniagent" / "sessions")
    skills_dir: Path = field(default_factory=lambda: Path.cwd() / "skills")
    log_level: str = "WARNING"
    tool_timeout: int = 30
    shell_timeout: int = 60
    shell_enabled: bool = True
    require_shell_confirmation: bool = True
    file_write_confirmation: bool = True
    max_tool_output_chars: int = 20000
    max_file_read_chars: int = 200000
    max_loaded_skills: int = 3
    mcp_enabled: bool = False
    mcp_config_path: Path = field(default_factory=lambda: Path.home() / ".miniagent" / "mcp.json")
    mcp_tool_timeout: int = 30
    mcp_servers: List[McpServerConfig] = field(default_factory=list)

    def validate_required(self) -> None:
        """Raise ValueError when required config is missing."""

        missing = []
        if not self.api_key:
            missing.append("api_key")
        if not self.model:
            missing.append("model")
        if missing:
            joined = ", ".join(missing)
            raise ValueError("Missing required configuration: " + joined)

    def with_updates(self, **updates: Any) -> "AgentConfig":
        """Return a copy with selected fields updated."""

        return replace(self, **updates)

