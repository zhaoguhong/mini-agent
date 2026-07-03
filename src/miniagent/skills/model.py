"""Skill data models."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List


@dataclass(frozen=True)
class SkillIndexItem:
    """The small skill index exposed to the model by default."""

    name: str
    description: str


@dataclass(frozen=True)
class Skill:
    """A local skill backed by SKILL.md and optional resource files."""

    name: str
    description: str
    resources: List[str]
    instructions: str
    root: Path

    def index_item(self) -> SkillIndexItem:
        """Return the minimal model-visible representation."""

        return SkillIndexItem(name=self.name, description=self.description)


@dataclass
class SkillState:
    """Tracks skills loaded during a conversation."""

    loaded_names: set[str] = field(default_factory=set)
