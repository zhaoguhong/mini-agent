import tempfile
import unittest
from pathlib import Path

from miniagent.config.schema import AgentConfig
from miniagent.skills.loader import SkillRepository
from miniagent.tools.base import ToolContext
from miniagent.tools.skill_tools import LoadSkillTool


class SkillTests(unittest.TestCase):
    def test_skill_index_is_minimal(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp_path = Path(raw)
            skill_dir = tmp_path / "skills" / "demo"
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text(
                "---\nname: demo\ndescription: Demo skill\ntriggers:\n  - hidden\n---\nSecret body",
                encoding="utf-8",
            )
            repo = SkillRepository(tmp_path / "skills")
            repo.discover()

            index = repo.index()

            self.assertEqual(index[0].name, "demo")
            self.assertEqual(index[0].description, "Demo skill")
            self.assertFalse(hasattr(index[0], "triggers"))

    def test_load_skill_returns_instructions_and_references(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp_path = Path(raw)
            skill_dir = tmp_path / "skills" / "demo"
            ref_dir = skill_dir / "references"
            ref_dir.mkdir(parents=True)
            (ref_dir / "example.md").write_text("Example", encoding="utf-8")
            (skill_dir / "SKILL.md").write_text(
                "---\nname: demo\ndescription: Demo skill\nreferences:\n  - references/example.md\n---\nInstructions",
                encoding="utf-8",
            )
            repo = SkillRepository(tmp_path / "skills")
            repo.discover()
            tool = LoadSkillTool(repo)
            config = AgentConfig(workspace_root=tmp_path)

            result = tool.run({"name": "demo"}, ToolContext(config=config))
            reference = tool.run({"name": "demo", "reference": "references/example.md"}, ToolContext(config=config))

            self.assertTrue(result.ok)
            self.assertIn("Instructions", result.content)
            self.assertTrue(reference.ok)
            self.assertEqual(reference.content, "Example")


if __name__ == "__main__":
    unittest.main()
