import tempfile
import unittest
from pathlib import Path

from miniagent.config.schema import AgentConfig
from miniagent.tools.base import ToolContext
from miniagent.tools.files import EditFileTool, ReadFileTool, SearchTextTool, WriteFileTool
from miniagent.tools.shell import RunShellTool


class ToolTests(unittest.TestCase):
    def test_read_file_rejects_outside_workspace(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp_path = Path(raw)
            tool = ReadFileTool()
            config = AgentConfig(workspace_root=tmp_path)

            result = tool.run({"path": "../secret.txt"}, ToolContext(config=config))

            self.assertFalse(result.ok)
            self.assertIn("outside workspace", result.error)

    def test_edit_file_replaces_exact_text(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp_path = Path(raw)
            path = tmp_path / "note.md"
            path.write_text("hello old world", encoding="utf-8")
            tool = EditFileTool()
            config = AgentConfig(workspace_root=tmp_path)

            result = tool.run(
                {"path": "note.md", "old_text": "old", "new_text": "new"},
                ToolContext(config=config),
            )

            self.assertTrue(result.ok)
            self.assertEqual(path.read_text(encoding="utf-8"), "hello new world")

    def test_write_file_creates_workspace_file(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp_path = Path(raw)
            path = tmp_path / "note.md"
            tool = WriteFileTool()
            config = AgentConfig(workspace_root=tmp_path)

            result = tool.run(
                {"path": "note.md", "content": "hello"},
                ToolContext(config=config),
            )

            self.assertTrue(result.ok)
            self.assertEqual(path.read_text(encoding="utf-8"), "hello")

    def test_write_file_rejects_outside_workspace(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp_path = Path(raw)
            tool = WriteFileTool()
            config = AgentConfig(workspace_root=tmp_path)

            result = tool.run(
                {"path": "../note.md", "content": "hello"},
                ToolContext(config=config),
            )

            self.assertFalse(result.ok)
            self.assertIn("outside workspace", result.error)

    def test_search_text_finds_match(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp_path = Path(raw)
            path = tmp_path / "note.md"
            path.write_text("alpha\nbeta\n", encoding="utf-8")
            tool = SearchTextTool()
            config = AgentConfig(workspace_root=tmp_path)

            result = tool.run({"query": "beta"}, ToolContext(config=config))

            self.assertTrue(result.ok)
            self.assertIn("note.md:2", result.content)

    def test_shell_denies_dangerous_command(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp_path = Path(raw)
            tool = RunShellTool()
            config = AgentConfig(workspace_root=tmp_path)

            result = tool.run({"command": "rm -rf /"}, ToolContext(config=config))

            self.assertFalse(result.ok)
            self.assertIn("denied", result.error.lower())

    def test_shell_runs_safe_command_without_confirmation(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp_path = Path(raw)
            tool = RunShellTool()
            config = AgentConfig(workspace_root=tmp_path)

            result = tool.run({"command": "echo hello"}, ToolContext(config=config))

            self.assertTrue(result.ok)
            self.assertEqual(result.content, "hello")

    def test_shell_requires_confirmation_for_sensitive_command(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp_path = Path(raw)
            tool = RunShellTool()
            config = AgentConfig(workspace_root=tmp_path)

            result = tool.run({"command": "touch note.txt"}, ToolContext(config=config))

            self.assertFalse(result.ok)
            self.assertIn("denied", result.error.lower())
            self.assertFalse((tmp_path / "note.txt").exists())

    def test_shell_requires_confirmation_for_chained_sensitive_command(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp_path = Path(raw)
            tool = RunShellTool()
            config = AgentConfig(workspace_root=tmp_path)

            result = tool.run({"command": "echo hello; touch note.txt"}, ToolContext(config=config))

            self.assertFalse(result.ok)
            self.assertIn("denied", result.error.lower())
            self.assertFalse((tmp_path / "note.txt").exists())

    def test_shell_runs_sensitive_command_after_confirmation(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp_path = Path(raw)
            tool = RunShellTool()
            config = AgentConfig(workspace_root=tmp_path)

            result = tool.run(
                {"command": "touch note.txt"},
                ToolContext(config=config, extras={"confirm": lambda prompt: True}),
            )

            self.assertTrue(result.ok)
            self.assertTrue((tmp_path / "note.txt").exists())


if __name__ == "__main__":
    unittest.main()
