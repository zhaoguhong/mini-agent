"""Local skill loading.

This module intentionally implements skill discovery itself instead of relying on
an external skill framework. Only a minimal index is exposed until load_skill is
called by the model.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from miniagent.skills.model import Skill, SkillIndexItem

logger = logging.getLogger(__name__)

FRONT_MATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?(.*)\Z", re.DOTALL)
RESOURCE_DIR_NAMES = (
    "references",
    "reference",
    "docs",
    "examples",
    "assets",
    "resources",
    "templates",
    "snippets",
)
MAX_SKILL_RESOURCES = 100
MAX_RESOURCE_PATH_CHARS = 512


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

        skills: Dict[str, Skill] = {}
        if self.skills_dir.exists():
            for path in sorted(self.skills_dir.glob("*/SKILL.md")):
                skill = self._load_skill_file(path)
                skills[skill.name] = skill
        self._skills = skills

    def index(self) -> List[SkillIndexItem]:
        """Return the minimal skill index exposed to the model."""

        return [self._skills[name].index_item() for name in sorted(self._skills)]

    def get(self, name: str) -> Skill:
        """Return a discovered skill by name."""

        try:
            return self._skills[name]
        except KeyError as exc:
            raise KeyError(f"Unknown skill: {name}") from exc

    def load_resource(self, name: str, resource: str) -> str:
        """Load an available resource file from inside a skill resource directory.

        Resources are discovered from known resource directories and must be
        requested by their full relative path. This keeps loading explicit while
        preventing path traversal outside the skill's resource directories.
        """

        skill = self.get(name)
        if resource not in skill.resources:
            raise ValueError(f"Resource is not available for skill: {resource}")
        path = (skill.root / resource).resolve()
        allowed_roots = [(skill.root / dirname).resolve() for dirname in RESOURCE_DIR_NAMES]
        if not any(_is_relative_to(path, root) for root in allowed_roots):
            raise ValueError("Resource path escapes skill resource directories")
        return path.read_text(encoding="utf-8")

    def _load_skill_file(self, path: Path) -> Skill:
        raw = path.read_text(encoding="utf-8")
        metadata, body = _split_front_matter(raw)
        name = str(metadata.get("name") or path.parent.name)
        description = str(metadata.get("description") or "")
        resources = _discover_resources(path.parent)
        return Skill(
            name=name,
            description=description,
            resources=resources,
            instructions=body.strip(),
            root=path.parent,
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


def _discover_resources(skill_root: Path) -> List[str]:
    """Return resource files discovered under known resource directories."""

    resources: List[str] = []
    for dirname in RESOURCE_DIR_NAMES:
        resource_dir = skill_root / dirname
        if not resource_dir.exists() or not resource_dir.is_dir() or resource_dir.is_symlink():
            continue
        for path in resource_dir.rglob("*"):
            if not path.is_file() or path.is_symlink():
                continue
            relative = path.relative_to(skill_root)
            if _should_skip_resource(relative):
                continue
            resource = relative.as_posix()
            if len(resource) > MAX_RESOURCE_PATH_CHARS:
                logger.warning(
                    "Skipping skill resource with overlong path: skill_root=%s resource=%s max_chars=%s",
                    skill_root,
                    resource,
                    MAX_RESOURCE_PATH_CHARS,
                )
                continue
            resources.append(resource)
            if len(resources) >= MAX_SKILL_RESOURCES:
                logger.warning(
                    "Reached skill resource limit: skill_root=%s max_resources=%s",
                    skill_root,
                    MAX_SKILL_RESOURCES,
                )
                return sorted(resources)
    return sorted(resources)


def _should_skip_resource(relative: Path) -> bool:
    """Return True when a resource path should stay hidden from skill loading."""

    return any(part.startswith(".") or part == "__pycache__" for part in relative.parts)


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False
