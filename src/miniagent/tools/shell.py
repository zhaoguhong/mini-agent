"""Restricted synchronous shell tool."""

from __future__ import annotations

import shlex
import subprocess
from typing import Any, Dict, Optional

from miniagent.tools.base import ToolContext, ToolResult


class RunShellTool:
    """Tool for synchronous workspace-scoped shell execution."""

    name = "run_shell"
    description = "Run a synchronous shell command inside the workspace with safety checks."
    parameters_schema = {
        "type": "object",
        "properties": {"command": {"type": "string"}},
        "required": ["command"],
        "additionalProperties": False,
    }

    def run(self, arguments: Dict[str, Any], context: ToolContext) -> ToolResult:
        """Run one synchronous command under the configured workspace policy."""

        if not context.config.shell_enabled:
            return ToolResult(ok=False, content="", error="Shell tool is disabled")
        command = arguments["command"]
        denied = _deny_reason(command)
        if denied:
            return ToolResult(ok=False, content="", error=denied)
        if context.config.require_shell_confirmation and not _confirm(context, f"Run shell command: {command}?"):
            return ToolResult(ok=False, content="", error="Shell command denied")
        try:
            completed = subprocess.run(
                command,
                cwd=str(context.config.workspace_root),
                shell=True,
                text=True,
                capture_output=True,
                timeout=context.config.shell_timeout,
            )
            output = completed.stdout
            if completed.stderr:
                output += ("\n" if output else "") + completed.stderr
            return ToolResult(
                ok=completed.returncode == 0,
                content=output.strip(),
                error=None if completed.returncode == 0 else f"Command exited with {completed.returncode}: {output.strip()}",
                metadata={"returncode": completed.returncode},
            )
        except subprocess.TimeoutExpired:
            return ToolResult(ok=False, content="", error=f"Shell command timed out after {context.config.shell_timeout}s")
        except Exception as exc:
            return ToolResult(ok=False, content="", error=str(exc))


def _deny_reason(command: str) -> Optional[str]:
    lowered = command.lower()
    dangerous_fragments = [
        "sudo ",
        "rm -rf",
        "mkfs",
        "dd if=",
        "chmod -r 777",
        "chown -r",
        "git reset --hard",
        "git checkout --",
    ]
    for fragment in dangerous_fragments:
        if fragment in lowered:
            return f"Command denied by safety policy: {fragment.strip()}"
    try:
        tokens = shlex.split(command)
    except ValueError:
        return "Command could not be parsed safely"
    if tokens and tokens[0] in {"sudo"}:
        return "Command denied by safety policy"
    return None


def _confirm(context: ToolContext, prompt: str) -> bool:
    callback = context.extras.get("confirm")
    if callback is None:
        return False
    return bool(callback(prompt))
