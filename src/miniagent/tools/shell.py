"""Restricted synchronous shell tool."""

from __future__ import annotations

import re
import shlex
import subprocess
from typing import Any, Dict, Optional

from miniagent.tools.base import ToolContext, ToolResult


class RunShellTool:
    """Tool for synchronous workspace-scoped shell execution.

    Most read-only commands should run without interruption. Commands that are
    destructive, change repository state, install software, or commonly write
    files require explicit confirmation, while clearly dangerous commands are
    denied before any prompt is shown.
    """

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
        if _requires_confirmation(command, context.config.require_shell_confirmation) and not _confirm(
            context, f"Run sensitive shell command: {command}?"
        ):
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


def _requires_confirmation(command: str, confirm_all: bool) -> bool:
    """Return whether a command should pause for user approval.

    This is a deliberately conservative string policy. It is not meant to prove
    a command safe; it only keeps common read-only commands smooth while putting
    obvious write, install, network-script, and VCS state changes behind a
    human confirmation step.
    """

    if confirm_all:
        return True
    lowered = command.lower()
    sensitive_fragments = [
        ">",
        ">>",
        "<<",
        "| sh",
        "| bash",
        "curl ",
        "wget ",
        "pip install",
        "python -m pip install",
        "npm install",
        "pnpm install",
        "yarn add",
        "brew install",
        "git add",
        "git commit",
        "git push",
        "git pull",
        "git merge",
        "git rebase",
        "git checkout",
        "git switch",
        "git restore",
        "git clean",
    ]
    if any(fragment in lowered for fragment in sensitive_fragments):
        return True

    writable_commands = {
        "rm",
        "rmdir",
        "mv",
        "cp",
        "mkdir",
        "touch",
        "chmod",
        "chown",
        "ln",
        "tee",
        "sed",
        "perl",
    }
    for tokens in _command_segments(command):
        if not tokens:
            continue
        command_name = tokens[0].rsplit("/", 1)[-1]
        if command_name == "__parse_error__":
            return True
        if command_name in {"sed", "perl"}:
            if any(token in {"-i", "-pi"} or token.startswith("-i") for token in tokens[1:]):
                return True
            continue
        if command_name in {"python", "python3"} and tokens[1:4] == ["-m", "pip", "install"]:
            return True
        if command_name in writable_commands:
            return True
    return False


def _command_segments(command: str) -> list[list[str]]:
    """Split common shell command chains into executable segments."""

    segments: list[list[str]] = []
    for raw_segment in re.split(r"\s*(?:&&|\|\||;|\|)\s*", command):
        try:
            segments.append(shlex.split(raw_segment))
        except ValueError:
            return [["__parse_error__"]]
    return segments


def _confirm(context: ToolContext, prompt: str) -> bool:
    callback = context.extras.get("confirm")
    if callback is None:
        return False
    return bool(callback(prompt))
