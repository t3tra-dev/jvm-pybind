from importlib.abc import Loader
from importlib.machinery import ModuleSpec
from types import ModuleType
from typing import Any, Optional

from ..classpath import ClasspathIndex
from ..jvm import JVM
from ..proxy import PackageProxy


class JavaLoader(Loader):
    """Javaローダー"""

    def __init__(
        self,
        jvm: JVM,
        fullname: str,
        classpath_index: Optional[ClasspathIndex] = None,
    ):
        self.jvm = jvm
        self.fullname = fullname
        self.classpath_index = classpath_index

    def create_module(self, spec: Optional[ModuleSpec]) -> ModuleType:
        if spec is None:
            raise ValueError("ModuleSpec cannot be None")
        return ModuleType(spec.name)

    def exec_module(self, module: ModuleType) -> None:
        def _lazy_attr(name: str) -> Any:
            if self.fullname in {"java", "javax", "jdk"}:
                return PackageProxy(
                    self.jvm,
                    f"{self.fullname}.{name}",
                    self.classpath_index,
                )
            package = PackageProxy(self.jvm, self.fullname, self.classpath_index)
            return getattr(package, name)

        module.__path__ = []
        setattr(module, "__getattr__", _lazy_attr)
        if "." not in self.fullname:
            setattr(module, "__repr__", lambda: "<Java root package>")
        else:
            setattr(module, "__repr__", lambda: f"<Java package {self.fullname}>")
