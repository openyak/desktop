"""Skill registry — discovers and manages SKILL.md files."""

from __future__ import annotations

import logging
from pathlib import Path

from app.skill.model import SkillInfo, parse_skill_file

logger = logging.getLogger(__name__)

# Directories under a project root (or home dir) that may contain skills.
_EXTERNAL_SKILL_DIRS = [".claude", ".agents"]
_OPENYAK_SKILL_DIR = ".openyak"


class SkillRegistry:
    """Discovers, stores, and retrieves skill definitions.

    Discovery order (lowest → highest priority):
      1. Bundled skills shipped with the application
      2. Global user skills  (~/.openyak/skills/)
      3. External skills     ({project}/.claude/skills/, {project}/.agents/skills/)
      4. Project skills      ({project}/.openyak/skills/)

    Later-discovered skills with the same name override earlier ones.
    """

    def __init__(self, bundled_dir: Path | None = None) -> None:
        self._skills: dict[str, SkillInfo] = {}
        self._bundled_dir = bundled_dir

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    def scan(self, project_dir: str | None = None) -> None:
        """Scan multiple directories for SKILL.md files.

        Args:
            project_dir: The project working directory. If provided, project-
                         level and external skill directories are searched.
        """
        search_dirs: list[Path] = []

        # 1. Bundled skills (lowest priority)
        if self._bundled_dir and self._bundled_dir.is_dir():
            search_dirs.append(self._bundled_dir)

        # 2. Global user skills
        home = Path.home()
        global_dir = home / _OPENYAK_SKILL_DIR / "skills"
        if global_dir.is_dir():
            search_dirs.append(global_dir)

        if project_dir:
            project = Path(project_dir).resolve()

            # 3. External directories (.claude/skills, .agents/skills)
            for ext in _EXTERNAL_SKILL_DIRS:
                ext_dir = project / ext / "skills"
                if ext_dir.is_dir():
                    search_dirs.append(ext_dir)

            # 4. Project-level .openyak/skills (highest priority)
            proj_dir = project / _OPENYAK_SKILL_DIR / "skills"
            if proj_dir.is_dir():
                search_dirs.append(proj_dir)

        # Scan each directory for **/SKILL.md
        for base in search_dirs:
            self._scan_directory(base)

        logger.info("Discovered %d skill(s)", len(self._skills))

    def _scan_directory(self, directory: Path) -> None:
        """Recursively find and parse SKILL.md files under *directory*."""
        for skill_path in sorted(directory.rglob("SKILL.md")):
            skill = parse_skill_file(skill_path)
            if skill is None:
                continue

            if skill.name in self._skills:
                logger.debug(
                    "Skill '%s' overridden: %s -> %s",
                    skill.name,
                    self._skills[skill.name].location,
                    skill.location,
                )

            self._skills[skill.name] = skill

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, skill: SkillInfo) -> None:
        """Register a skill programmatically (e.g. from plugin loader)."""
        self._skills[skill.name] = skill

    def unregister(self, name: str) -> bool:
        """Remove a skill by name. Returns True if it existed."""
        return self._skills.pop(name, None) is not None

    # ------------------------------------------------------------------
    # Lookup
    # ------------------------------------------------------------------

    def get(self, name: str) -> SkillInfo | None:
        """Get a skill by name."""
        return self._skills.get(name)

    def all_skills(self) -> list[SkillInfo]:
        """Return all discovered skills."""
        return list(self._skills.values())

    def skill_names(self) -> list[str]:
        """Return names of all discovered skills."""
        return list(self._skills.keys())

    @property
    def count(self) -> int:
        """Number of discovered skills."""
        return len(self._skills)
