"""Workspace-scoped file tools."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List

from miniagent.storage.paths import ensure_dir, resolve_workspace_path
from miniagent.tools.base import ToolContext, ToolResult


class ReadFileTool:
    """Tool for reading workspace-scoped text files."""

    name = "read_file"
    description = "Read a UTF-8 text file inside the workspace."
    parameters_schema = {
        "type": "object",
        "properties": {"path": {"type": "string"}},
        "required": ["path"],
        "additionalProperties": False,
    }

    def run(self, arguments: Dict[str, Any], context: ToolContext) -> ToolResult:
        """Read a workspace-scoped text file with output truncation."""

        try:
            path = resolve_workspace_path(context.config.workspace_root, arguments["path"])
            text = path.read_text(encoding="utf-8")
            if len(text) > context.config.max_file_read_chars:
                text = text[: context.config.max_file_read_chars] + "\n...[truncated]"
            return ToolResult(ok=True, content=text, metadata={"path": str(path)})
        except Exception as exc:
            return ToolResult(ok=False, content="", error=str(exc))


class WriteFileTool:
    """Tool for creating or replacing workspace-scoped text files."""

    name = "write_file"
    description = "Create or overwrite a UTF-8 text file inside the workspace."
    parameters_schema = {
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "content": {"type": "string"},
        },
        "required": ["path", "content"],
        "additionalProperties": False,
    }

    def run(self, arguments: Dict[str, Any], context: ToolContext) -> ToolResult:
        """Create or overwrite a workspace file after confirmation when required."""

        try:
            path = resolve_workspace_path(context.config.workspace_root, arguments["path"])
            ensure_dir(path.parent)
            path.write_text(arguments["content"], encoding="utf-8")
            return ToolResult(ok=True, content=f"Wrote {path}", metadata={"path": str(path)})
        except Exception as exc:
            return ToolResult(ok=False, content="", error=str(exc))


class EditFileTool:
    """Tool for exact, local text replacements in existing files.

    This tool intentionally avoids line-number patches and fuzzy matching. The
    model must provide the exact old text so edits are deterministic, reviewable,
    and easy to reject when the target text is missing or ambiguous.
    """

    name = "edit_file"
    description = "Replace an exact text segment in a UTF-8 file inside the workspace."
    parameters_schema = {
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "old_text": {"type": "string"},
            "new_text": {"type": "string"},
            "replace_all": {"type": "boolean", "default": False},
        },
        "required": ["path", "old_text", "new_text"],
        "additionalProperties": False,
    }

    def run(self, arguments: Dict[str, Any], context: ToolContext) -> ToolResult:
        """Apply an exact text replacement without guessing edit locations.

        Ambiguous single replacements are rejected instead of choosing the first
        match. That forces the model to read more context or opt into
        `replace_all`, which is safer for code and documentation edits.
        """

        try:
            path = resolve_workspace_path(context.config.workspace_root, arguments["path"])
            text = path.read_text(encoding="utf-8")
            old_text = arguments["old_text"]
            new_text = arguments["new_text"]
            replace_all = bool(arguments.get("replace_all", False))
            count = text.count(old_text)
            if count == 0:
                return ToolResult(ok=False, content="", error="old_text was not found")
            if count > 1 and not replace_all:
                # Ambiguous edits are rejected so the model must read more context.
                return ToolResult(ok=False, content="", error=f"old_text matched {count} times; set replace_all=true or provide more context")
            updated = text.replace(old_text, new_text) if replace_all else text.replace(old_text, new_text, 1)
            path.write_text(updated, encoding="utf-8")
            return ToolResult(ok=True, content=f"Edited {path}; replacements={count if replace_all else 1}", metadata={"path": str(path)})
        except Exception as exc:
            return ToolResult(ok=False, content="", error=str(exc))


class SearchTextTool:
    """Tool for text and regex search inside the workspace."""

    name = "search_text"
    description = "Search text or regex in workspace files."
    parameters_schema = {
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "path": {"type": "string", "default": "."},
            "regex": {"type": "boolean", "default": False},
            "max_results": {"type": "integer", "default": 50},
        },
        "required": ["query"],
        "additionalProperties": False,
    }

    def run(self, arguments: Dict[str, Any], context: ToolContext) -> ToolResult:
        """Search readable text files under the workspace."""

        try:
            root = resolve_workspace_path(context.config.workspace_root, arguments.get("path", "."))
            query = arguments["query"]
            regex = bool(arguments.get("regex", False))
            max_results = int(arguments.get("max_results", 50))
            pattern = re.compile(query) if regex else None
            results: List[str] = []
            files = [root] if root.is_file() else [p for p in root.rglob("*") if p.is_file()]
            for file_path in files:
                if len(results) >= max_results:
                    break
                if _skip_file(file_path):
                    continue
                try:
                    for line_no, line in enumerate(file_path.read_text(encoding="utf-8").splitlines(), start=1):
                        matched = bool(pattern.search(line)) if pattern else query in line
                        if matched:
                            rel = file_path.relative_to(context.config.workspace_root.resolve())
                            results.append(f"{rel}:{line_no}: {line}")
                            if len(results) >= max_results:
                                break
                except UnicodeDecodeError:
                    continue
            return ToolResult(ok=True, content="\n".join(results) if results else "No matches")
        except Exception as exc:
            return ToolResult(ok=False, content="", error=str(exc))


def _skip_file(path: Path) -> bool:
    ignored = {".git", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
    return any(part in ignored for part in path.parts)
