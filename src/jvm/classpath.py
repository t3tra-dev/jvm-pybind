from __future__ import annotations

import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Iterable


class ClasspathError(ValueError):
    """Raised when a classpath entry cannot be indexed."""


@dataclass(frozen=True)
class ClasspathIndex:
    """An import-oriented index of Java packages and classes."""

    classes: frozenset[str]
    packages: frozenset[str]

    @classmethod
    def empty(cls) -> ClasspathIndex:
        return cls(classes=frozenset(), packages=frozenset())

    @classmethod
    def from_entries(cls, entries: Iterable[str]) -> ClasspathIndex:
        classes: set[str] = set()

        for raw_entry in entries:
            entry = Path(raw_entry)
            if entry.is_dir():
                classes.update(cls._classes_from_directory(entry))
            elif entry.is_file() and entry.suffix.lower() in {".jar", ".zip"}:
                classes.update(cls._classes_from_archive(entry))
            elif entry.exists():
                raise ClasspathError(
                    f"Unsupported classpath entry (expected a JAR/ZIP or directory): {entry}"
                )
            else:
                raise ClasspathError(f"Classpath entry does not exist: {entry}")

        packages: set[str] = set()
        for class_name in classes:
            parts = class_name.split(".")[:-1]
            for index in range(1, len(parts) + 1):
                packages.add(".".join(parts[:index]))

        return cls(classes=frozenset(classes), packages=frozenset(packages))

    @staticmethod
    def _classes_from_directory(root: Path) -> set[str]:
        classes: set[str] = set()
        for class_file in root.rglob("*.class"):
            relative = class_file.relative_to(root).as_posix()
            class_name = ClasspathIndex._class_name_from_entry(relative)
            if class_name is not None:
                classes.add(class_name)
        return classes

    @staticmethod
    def _classes_from_archive(archive: Path) -> set[str]:
        try:
            with zipfile.ZipFile(archive) as jar:
                return {
                    class_name
                    for name in jar.namelist()
                    if (class_name := ClasspathIndex._class_name_from_entry(name))
                    is not None
                }
        except (OSError, zipfile.BadZipFile) as exc:
            raise ClasspathError(
                f"Failed to index classpath archive {archive}: {exc}"
            ) from exc

    @staticmethod
    def _class_name_from_entry(raw_name: str) -> str | None:
        path = PurePosixPath(raw_name)
        parts = list(path.parts)

        if len(parts) >= 4 and parts[:2] == ["META-INF", "versions"]:
            parts = parts[3:]
        elif parts and parts[0] == "META-INF":
            return None

        if not parts or not parts[-1].endswith(".class"):
            return None

        simple_name = parts[-1][:-6]
        if simple_name in {"module-info", "package-info"} or "$" in simple_name:
            return None

        parts[-1] = simple_name
        return ".".join(parts)

    def contains_package(self, fullname: str) -> bool:
        return fullname in self.packages

    def contains_class(self, fullname: str) -> bool:
        return fullname in self.classes
