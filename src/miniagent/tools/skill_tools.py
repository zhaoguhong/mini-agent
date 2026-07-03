"""Tools that expose skill content progressively."""

from __future__ import annotations

from typing import Any, Dict

from miniagent.skills.loader import SkillRepository
from miniagent.tools.base import ToolContext, ToolResult


class LoadSkillTool:
    """Tool for progressive disclosure of local skill content and resources.

    The model initially sees only skill names and descriptions. Calling this
    tool is the explicit step that brings full instructions and discovered
    resource paths into the conversation. Resource content is loaded only when
    requested by full relative path.
    """

    name = "load_skill"
    description = "Load a local skill's instructions or an optional resource file."
    parameters_schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "resource": {
                "type": "string",
                "description": "Optional full resource path from the skill's available resources list.",
            },
        },
        "required": ["name"],
        "additionalProperties": False,
    }

    def __init__(self, repository: SkillRepository) -> None:
        self.repository = repository

    def run(self, arguments: Dict[str, Any], context: ToolContext) -> ToolResult:
        """Load skill instructions first, then optional resource files.

        A call without `resource` returns the full skill metadata, available
        resource paths, and primary instructions. A call with `resource` returns
        only that file, so large examples stay out of context until the model
        asks for them.
        """

        try:
            unexpected = sorted(set(arguments) - {"name", "resource"})
            if unexpected:
                raise ValueError(f"Unexpected load_skill argument(s): {', '.join(unexpected)}")
            name = arguments["name"]
            resource = arguments.get("resource")
            if resource:
                content = self.repository.load_resource(name, resource)
                if len(content) > context.config.max_file_read_chars:
                    content = content[: context.config.max_file_read_chars] + "\n...[truncated]"
                return ToolResult(ok=True, content=content, metadata={"skill": name, "resource": resource})

            skill = self.repository.get(name)
            context.extras.setdefault("loaded_skills", set()).add(name)
            # The default skill index is intentionally tiny; full metadata is
            # disclosed only after the model chooses this skill.
            content = "\n".join(
                [
                    f"name: {skill.name}",
                    f"description: {skill.description}",
                    "available resources:",
                    *[f"- {item}" for item in skill.resources],
                    "",
                    skill.instructions,
                ]
            )
            if len(content) > context.config.max_tool_output_chars:
                content = content[: context.config.max_tool_output_chars] + "\n...[truncated]"
            return ToolResult(ok=True, content=content, metadata={"skill": name, "resources": skill.resources})
        except Exception as exc:
            return ToolResult(ok=False, content="", error=str(exc))
