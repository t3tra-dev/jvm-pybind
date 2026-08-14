import sys
import threading
from importlib.abc import MetaPathFinder
from importlib.machinery import ModuleSpec, PathFinder
from pathlib import Path
from typing import Any, Optional, Sequence

from ..classpath import ClasspathIndex
from ..config import Config
from ..jvm import JVM
from ..loader import JVMLoader
from ..logger import logger
from .loader import JavaLoader


class JavaFinder(MetaPathFinder):
    """Javaパッケージファインダー"""

    _PREFIXES = ("java.", "javax.", "jdk.")
    _ROOTS = ("java", "javax", "jdk")

    def __init__(self) -> None:
        self._jvm: Optional[JVM] = None
        self._config: Optional[Config] = None
        self._classpath_index: Optional[ClasspathIndex] = None
        self._config_discovery_key: Optional[tuple[str, str, str]] = None
        self._jvm_lock = threading.RLock()
        self._shutdown_registered = False

    def _get_config(self) -> Config:
        """Load and cache configuration from the entry project."""
        discovery_key = self._current_discovery_key()
        needs_refresh = self._config is None or (
            self._jvm is None and self._config_discovery_key != discovery_key
        )
        if needs_refresh:
            with self._jvm_lock:
                needs_refresh = self._config is None or (
                    self._jvm is None and self._config_discovery_key != discovery_key
                )
                if needs_refresh:
                    self._config = Config.from_pyproject()
                    self._classpath_index = None
                    self._config_discovery_key = discovery_key
        if self._config is None:
            raise RuntimeError("Failed to load JVM configuration")
        return self._config

    @staticmethod
    def _current_discovery_key() -> tuple[str, str, str]:
        entry = sys.path[0] if sys.path else ""
        argv_entry = sys.argv[0] if sys.argv else ""
        return (str(Path.cwd()), entry, argv_entry)

    def _get_classpath_index(self) -> ClasspathIndex:
        """Build the custom package index without starting the JVM."""
        if self._classpath_index is not None and self._config is None:
            return self._classpath_index
        config = self._get_config()
        if self._classpath_index is None:
            with self._jvm_lock:
                if self._classpath_index is None:
                    self._classpath_index = ClasspathIndex.from_entries(
                        config.classpath
                    )
        return self._classpath_index

    def _get_jvm(self) -> JVM:
        """遅延JVM初期化"""
        if self._jvm is None:
            with self._jvm_lock:
                if self._jvm is None:
                    logger.info("Initializing JVM...")
                    self._jvm = JVMLoader(self._get_config()).start()
                    logger.info("JVM initialized")

        return self._jvm

    def find_spec(
        self, fullname: str, path: Optional[Sequence[str]], target: Optional[Any] = None
    ) -> Optional[ModuleSpec]:
        is_standard_package = fullname in self._ROOTS or fullname.startswith(
            self._PREFIXES
        )

        if is_standard_package:
            jvm = self._get_jvm()
            return ModuleSpec(
                name=fullname,
                loader=JavaLoader(jvm, fullname),
                is_package=True,
            )

        python_spec = PathFinder.find_spec(fullname, path)
        if python_spec is not None and python_spec.loader is not None:
            return None

        classpath_index = self._get_classpath_index()
        is_custom_package = classpath_index.contains_package(fullname)

        if not is_custom_package:
            return None

        jvm = self._get_jvm()
        return ModuleSpec(
            name=fullname,
            loader=JavaLoader(jvm, fullname, classpath_index),
            is_package=True,
        )
