"""Local skill loading.

This module intentionally implements skill discovery itself instead of relying on
an external skill framework. Only a minimal index is exposed until load_skill is
called by the model.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from miniagent.skills.model import Skill, SkillIndexItem

FRONT_MATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?(.*)\Z", re.DOTALL)


class SkillRepository:
    """Discovers and loads local skills.

    Only skill metadata needed for routing is kept in the default index. Full
    instructions and reference files stay behind `load_skill`, which keeps the
    base prompt compact and makes skill activation visible in the transcript.
    """

    def __init__(self, skills_dir: Path) -> None:
        self.skills_dir = skills_dir
        self._skills: Dict[str, Skill] = {}

    def discover(self) -> None:
        """Scan the skills directory and refresh the in-memory index."""

        self._skills = {}
        if not self.skills_dir.exists():
            return
        for path in sorted(self.skills_dir.glob("*/SKILL.md")):
            skill = self._load_skill_file(path)
            self._skills[skill.name] = skill

    def index(self) -> List[SkillIndexItem]:
        """Return the minimal skill index exposed to the model."""

        return [self._skills[name].index_item() for name in sorted(self._skills)]

    def get(self, name: str) -> Skill:
        """Return a discovered skill by name."""

        try:
            return self._skills[name]
        except KeyError as exc:
            raise KeyError(f"Unknown skill: {name}") from exc

    def load_reference(self, name: str, reference: str) -> str:
        """Load a declared reference file from inside a skill directory.

        References must be listed by the skill and must resolve under that
        skill's root directory. This prevents a skill from using references as a
        path traversal mechanism.
        """

        skill = self.get(name)
        if reference not in skill.references:
            raise ValueError(f"Reference is not declared by skill: {reference}")
        path = (skill.root / reference).resolve()
        try:
            path.relative_to(skill.root.resolve())
        except ValueError as exc:
            raise ValueError("Reference path escapes skill directory") from exc
        return path.read_text(encoding="utf-8")

    def _load_skill_file(self, path: Path) -> Skill:
        raw = path.read_text(encoding="utf-8")
        metadata, body = _split_front_matter(raw)
        name = str(metadata.get("name") or path.parent.name)
        description = str(metadata.get("description") or "")
        triggers = _list(metadata.get("triggers"))
        references = _list(metadata.get("references"))
        return Skill(
            name=name,
            description=description,
            triggers=triggers,
            references=references,
            instructions=body.strip(),
            root=path.parent,
            source_path=path,
        )


def _split_front_matter(raw: str) -> Tuple[Dict[str, Any], str]:
    """Split optional front matter from markdown body."""

    match = FRONT_MATTER_RE.match(raw)
    if not match:
        return {}, raw
    return _parse_simple_yaml(match.group(1)), match.group(2)


def _parse_simple_yaml(raw: str) -> Dict[str, Any]:
    """Parse the small YAML subset used by SKILL.md metadata.

    The project only needs scalar fields and simple lists, so this parser keeps
    skill loading dependency-free. If SKILL.md metadata grows more complex, this
    should be replaced with a real YAML parser instead of expanding ad hoc rules.
    """

    result: Dict[str, Any] = {}
    current_list: Optional[str] = None
    for line in raw.splitlines():
        if not line.strip():
            continue
        if line.startswith("  - ") and current_list:
            result.setdefault(current_list, []).append(line[4:].strip().strip('"'))
            continue
        if ":" in line:
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip()
            if value:
                result[key] = value.strip('"')
                current_list = None
            else:
                result[key] = []
                current_list = key
    return result


def _list(value: Any) -> List[str]:
    """Normalize scalar or list metadata into a list of strings."""

    if not value:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    return [str(value)]
