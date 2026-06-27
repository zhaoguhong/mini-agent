"""Built-in tool registration."""

from miniagent.tools.files import EditFileTool, ReadFileTool, SearchTextTool, WriteFileTool
from miniagent.tools.registry import ToolRegistry
from miniagent.tools.shell import RunShellTool
from miniagent.tools.skill_tools import LoadSkillTool


def create_builtin_registry(skill_repository=None) -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(ReadFileTool())
    registry.register(WriteFileTool())
    registry.register(EditFileTool())
    registry.register(SearchTextTool())
    registry.register(RunShellTool())
    if skill_repository is not None:
        registry.register(LoadSkillTool(skill_repository))
    return registry
