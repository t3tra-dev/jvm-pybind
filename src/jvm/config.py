from __future__ import annotations

import sys
import tomllib
from dataclasses import dataclass
from glob import glob, has_magic
from pathlib import Path
from typing import Dict, List, Optional


class ConfigError(ValueError):
    """Raised when JVM configuration is present but invalid."""


@dataclass
class Config:
    """JVM設定"""

    java_version: str
    deps: Dict[str, List[str]]
    classpath: List[str]
    project_root: Optional[Path] = None
    pyproject_path: Optional[Path] = None

    @classmethod
    def from_pyproject(cls, search_path: Optional[str] = None) -> Config:
        """pyproject.toml設定読み込み"""
        pyproject_path = cls._find_pyproject_toml(search_path)

        if not pyproject_path:
            return cls(java_version="17", deps={}, classpath=[])

        try:
            with open(pyproject_path, "rb") as f:
                data = tomllib.load(f)
        except (OSError, tomllib.TOMLDecodeError) as exc:
            raise ConfigError(f"Failed to read {pyproject_path}: {exc}") from exc

        tool = data.get("tool", {})
        if not isinstance(tool, dict):
            raise ConfigError(f"[tool] must be a table in {pyproject_path}")

        tool_jvm = tool.get("jvm", {})
        if not isinstance(tool_jvm, dict):
            raise ConfigError(f"[tool.jvm] must be a table in {pyproject_path}")

        java_version = tool_jvm.get("java-version", "17")
        deps = tool_jvm.get("deps", {})
        classpath = tool_jvm.get("classpath", [])

        if not isinstance(java_version, str) or not java_version.strip():
            raise ConfigError(
                f"tool.jvm.java-version must be a non-empty string in {pyproject_path}"
            )
        if not isinstance(deps, dict):
            raise ConfigError(f"tool.jvm.deps must be a table in {pyproject_path}")
        if not isinstance(classpath, list) or not all(
            isinstance(entry, str) and entry.strip() for entry in classpath
        ):
            raise ConfigError(
                f"tool.jvm.classpath must be an array of non-empty strings in {pyproject_path}"
            )

        project_root = pyproject_path.parent.resolve()
        resolved_classpath = cls._resolve_classpath(classpath, project_root)

        return cls(
            java_version=java_version.strip(),
            deps=deps,
            classpath=resolved_classpath,
            project_root=project_root,
            pyproject_path=pyproject_path.resolve(),
        )

    @staticmethod
    def _resolve_classpath(classpath: List[str], project_root: Path) -> List[str]:
        """Resolve classpath entries relative to the declaring pyproject.toml."""
        resolved: List[str] = []
        seen: set[str] = set()

        for raw_entry in classpath:
            entry_path = Path(raw_entry).expanduser()
            candidate = (
                entry_path if entry_path.is_absolute() else project_root / entry_path
            )
            candidate_text = str(candidate)

            if has_magic(candidate_text):
                matches = sorted(
                    Path(match).resolve() for match in glob(candidate_text)
                )
                if not matches:
                    raise ConfigError(
                        f"Classpath pattern matched no files: {raw_entry!r} "
                        f"(from {project_root})"
                    )
            else:
                matches = [candidate.resolve()]

            for match in matches:
                if not match.exists():
                    raise ConfigError(
                        f"Classpath entry does not exist: {raw_entry!r} "
                        f"(resolved to {match})"
                    )
                normalized = str(match)
                if normalized not in seen:
                    seen.add(normalized)
                    resolved.append(normalized)

        return resolved

    @staticmethod
    def _find_pyproject_toml(search_path: Optional[str] = None) -> Optional[Path]:
        """pyproject.toml検索"""
        if search_path:
            requested = Path(search_path).expanduser()
            if requested.is_file():
                return requested if requested.name == "pyproject.toml" else None
            return Config._search_parents(requested)

        entry_dir = Path(sys.path[0]) if sys.path[0] else Path.cwd()
        entry_result = Config._search_parents(entry_dir)
        if entry_result is not None:
            return entry_result

        cwd = Path.cwd()
        if entry_dir.resolve() != cwd.resolve():
            return Config._search_parents(cwd)
        return None

    @staticmethod
    def _search_parents(start: Path) -> Optional[Path]:
        """Search start and its parents for pyproject.toml."""
        current_dir = start.absolute()
        while True:
            pyproject_path = current_dir / "pyproject.toml"
            if pyproject_path.exists():
                return pyproject_path

            parent = current_dir.parent
            if parent == current_dir:
                break
            current_dir = parent

        return None
