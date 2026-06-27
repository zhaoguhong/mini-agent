"""Tools that expose skill content progressively."""

from __future__ import annotations

from typing import Any, Dict

from miniagent.skills.loader import SkillRepository
from miniagent.tools.base import ToolContext, ToolResult


class LoadSkillTool:
    """Tool for progressive disclosure of local skill content.

    The model initially sees only skill names and descriptions. Calling this
    tool is the explicit step that brings full instructions, triggers, and
    declared reference files into the conversation.
    """

    name = "load_skill"
    description = "Load a local skill's full instructions, metadata, or a declared reference file."
    parameters_schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "reference": {
                "type": "string",
                "description": "Optional declared reference path to load from the skill directory.",
            },
        },
        "required": ["name"],
        "additionalProperties": False,
    }

    def __init__(self, repository: SkillRepository) -> None:
        self.repository = repository

    def run(self, arguments: Dict[str, Any], context: ToolContext) -> ToolResult:
        """Load skill instructions first, then optional declared references.

        A call without `reference` returns the full skill metadata and primary
        instructions. A call with `reference` returns only that declared file, so
        large examples stay out of context until the model asks for them.
        """

        try:
            name = arguments["name"]
            reference = arguments.get("reference")
            if reference:
                content = self.repository.load_reference(name, reference)
                if len(content) > context.config.max_file_read_chars:
                    content = content[: context.config.max_file_read_chars] + "\n...[truncated]"
                return ToolResult(ok=True, content=content, metadata={"skill": name, "reference": reference})

            skill = self.repository.get(name)
            context.extras.setdefault("loaded_skills", set()).add(name)
            # The default skill index is intentionally tiny; full metadata is
            # disclosed only after the model chooses this skill.
            content = "\n".join(
                [
                    f"name: {skill.name}",
                    f"description: {skill.description}",
                    "triggers:",
                    *[f"- {item}" for item in skill.triggers],
                    "references:",
                    *[f"- {item}" for item in skill.references],
                    "",
                    skill.instructions,
                ]
            )
            if len(content) > context.config.max_tool_output_chars:
                content = content[: context.config.max_tool_output_chars] + "\n...[truncated]"
            return ToolResult(ok=True, content=content, metadata={"skill": name, "references": skill.references})
        except Exception as exc:
            return ToolResult(ok=False, content="", error=str(exc))
