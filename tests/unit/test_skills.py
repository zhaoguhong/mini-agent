import tempfile
import unittest
from pathlib import Path

from miniagent.config.schema import AgentConfig
from miniagent.skills.loader import MAX_RESOURCE_PATH_CHARS, MAX_SKILL_RESOURCES, SkillRepository
from miniagent.tools.base import ToolContext
from miniagent.tools.skill_tools import LoadSkillTool


class SkillTests(unittest.TestCase):
    def test_skill_index_is_minimal(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp_path = Path(raw)
            skill_dir = tmp_path / "skills" / "demo"
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text(
                "---\nname: demo\ndescription: Demo skill\n---\nSecret body",
                encoding="utf-8",
            )
            repo = SkillRepository(tmp_path / "skills")
            repo.discover()

            index = repo.index()

            self.assertEqual(index[0].name, "demo")
            self.assertEqual(index[0].description, "Demo skill")
            self.assertFalse(hasattr(index[0], "resources"))

    def test_load_skill_returns_instructions_and_resources(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp_path = Path(raw)
            skill_dir = tmp_path / "skills" / "demo"
            ref_dir = skill_dir / "references"
            ref_dir.mkdir(parents=True)
            (ref_dir / "example.md").write_text("Example", encoding="utf-8")
            (skill_dir / "SKILL.md").write_text(
                "---\nname: demo\ndescription: Demo skill\n---\nInstructions",
                encoding="utf-8",
            )
            repo = SkillRepository(tmp_path / "skills")
            repo.discover()
            tool = LoadSkillTool(repo)
            config = AgentConfig(workspace_root=tmp_path)

            result = tool.run({"name": "demo"}, ToolContext(config=config))
            resource = tool.run({"name": "demo", "resource": "references/example.md"}, ToolContext(config=config))

            self.assertTrue(result.ok)
            self.assertIn("Instructions", result.content)
            self.assertIn("available resources:", result.content)
            self.assertIn("- references/example.md", result.content)
            self.assertNotIn("\nExample", result.content)
            self.assertTrue(resource.ok)
            self.assertEqual(resource.content, "Example")

    def test_resources_are_discovered_from_default_directories(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp_path = Path(raw)
            skill_dir = tmp_path / "skills" / "demo"
            resource_paths = [
                "references/a.md",
                "reference/b.md",
                "docs/c.md",
                "examples/d.py",
                "assets/e.txt",
                "resources/f.md",
                "templates/g.txt",
                "snippets/h.py",
                "docs/tutorial/part1.md",
            ]
            for item in resource_paths:
                path = skill_dir / item
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(item, encoding="utf-8")
            (skill_dir / "docs" / ".hidden.md").write_text("hidden", encoding="utf-8")
            cache_dir = skill_dir / "docs" / "__pycache__"
            cache_dir.mkdir()
            (cache_dir / "ignored.pyc").write_text("ignored", encoding="utf-8")
            (skill_dir / "other").mkdir(parents=True)
            (skill_dir / "other" / "ignored.md").write_text("ignored", encoding="utf-8")
            (skill_dir / "SKILL.md").write_text(
                "---\nname: demo\ndescription: Demo skill\n---\nInstructions",
                encoding="utf-8",
            )
            repo = SkillRepository(tmp_path / "skills")
            repo.discover()

            resources = repo.get("demo").resources

            self.assertEqual(resources, sorted(resource_paths))

    def test_resource_requires_full_discovered_path(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp_path = Path(raw)
            skill_dir = tmp_path / "skills" / "demo"
            ref_dir = skill_dir / "references"
            ref_dir.mkdir(parents=True)
            (ref_dir / "example.md").write_text("Example", encoding="utf-8")
            (skill_dir / "SKILL.md").write_text(
                "---\nname: demo\ndescription: Demo skill\n---\nInstructions",
                encoding="utf-8",
            )
            repo = SkillRepository(tmp_path / "skills")
            repo.discover()
            tool = LoadSkillTool(repo)
            config = AgentConfig(workspace_root=tmp_path)

            result = tool.run({"name": "demo", "resource": "example.md"}, ToolContext(config=config))

            self.assertFalse(result.ok)
            self.assertIn("Resource is not available", result.error or "")

    def test_resource_discovery_limits_resource_count(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp_path = Path(raw)
            skill_dir = tmp_path / "skills" / "demo"
            ref_dir = skill_dir / "references"
            ref_dir.mkdir(parents=True)
            for index in range(MAX_SKILL_RESOURCES + 5):
                (ref_dir / f"{index:03}.md").write_text(str(index), encoding="utf-8")
            (skill_dir / "SKILL.md").write_text(
                "---\nname: demo\ndescription: Demo skill\n---\nInstructions",
                encoding="utf-8",
            )
            repo = SkillRepository(tmp_path / "skills")
            with self.assertLogs("miniagent.skills.loader", level="WARNING") as logs:
                repo.discover()

            resources = repo.get("demo").resources

            self.assertEqual(len(resources), MAX_SKILL_RESOURCES)
            self.assertTrue(any("Reached skill resource limit" in item for item in logs.output))

    def test_resource_discovery_skips_overlong_paths(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp_path = Path(raw)
            skill_dir = tmp_path / "skills" / "demo"
            ref_dir = skill_dir / "references"
            ref_dir.mkdir(parents=True)
            short_path = ref_dir / "short.md"
            short_path.write_text("short", encoding="utf-8")
            long_path = ref_dir / ("a" * 200) / ("b" * 200) / ("c" * 120) / "long.md"
            self.assertGreater(len(long_path.relative_to(skill_dir).as_posix()), MAX_RESOURCE_PATH_CHARS)
            long_path.parent.mkdir(parents=True)
            long_path.write_text("long", encoding="utf-8")
            (skill_dir / "SKILL.md").write_text(
                "---\nname: demo\ndescription: Demo skill\n---\nInstructions",
                encoding="utf-8",
            )
            repo = SkillRepository(tmp_path / "skills")
            with self.assertLogs("miniagent.skills.loader", level="WARNING") as logs:
                repo.discover()

            resources = repo.get("demo").resources

            self.assertEqual(resources, ["references/short.md"])
            self.assertTrue(any("Skipping skill resource with overlong path" in item for item in logs.output))

    def test_resource_path_escape_is_rejected(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp_path = Path(raw)
            skill_dir = tmp_path / "skills" / "demo"
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text(
                "---\nname: demo\ndescription: Demo skill\n---\nInstructions",
                encoding="utf-8",
            )
            repo = SkillRepository(tmp_path / "skills")
            repo.discover()
            tool = LoadSkillTool(repo)
            config = AgentConfig(workspace_root=tmp_path)

            result = tool.run({"name": "demo", "resource": "../SKILL.md"}, ToolContext(config=config))

            self.assertFalse(result.ok)
            self.assertIn("Resource is not available", result.error or "")

    def test_undiscovered_files_cannot_be_loaded_as_resources(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp_path = Path(raw)
            skill_dir = tmp_path / "skills" / "demo"
            other_dir = skill_dir / "other"
            other_dir.mkdir(parents=True)
            (other_dir / "example.md").write_text("Example", encoding="utf-8")
            (skill_dir / "SKILL.md").write_text(
                "---\nname: demo\ndescription: Demo skill\n---\nInstructions",
                encoding="utf-8",
            )
            repo = SkillRepository(tmp_path / "skills")
            repo.discover()
            tool = LoadSkillTool(repo)
            config = AgentConfig(workspace_root=tmp_path)

            result = tool.run({"name": "demo", "resource": "other/example.md"}, ToolContext(config=config))

            self.assertFalse(result.ok)
            self.assertIn("Resource is not available", result.error or "")

    def test_old_reference_argument_is_rejected(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp_path = Path(raw)
            skill_dir = tmp_path / "skills" / "demo"
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text(
                "---\nname: demo\ndescription: Demo skill\n---\nInstructions",
                encoding="utf-8",
            )
            repo = SkillRepository(tmp_path / "skills")
            repo.discover()
            tool = LoadSkillTool(repo)
            config = AgentConfig(workspace_root=tmp_path)

            result = tool.run({"name": "demo", "reference": "references/example.md"}, ToolContext(config=config))

            self.assertFalse(result.ok)
            self.assertIn("Unexpected load_skill argument", result.error or "")


if __name__ == "__main__":
    unittest.main()
