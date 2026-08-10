"""End-to-end coverage for project-local Java libraries."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from jvm.config import Config
from jvm.loader import JVMLoader


def test_hello_jar_import_from_repository_root() -> None:
    repository_root = Path(__file__).resolve().parents[1]
    example_dir = repository_root / "examples" / "hello"
    config = Config.from_pyproject(str(example_dir))

    assert config.java_version == "21"
    assert config.classpath == [str((example_dir / "hello.jar").resolve())]

    try:
        JVMLoader(config)._find_libjvm(config.java_version)
    except RuntimeError:
        pytest.skip("Java 21 is not available for the hello example")

    completed = subprocess.run(
        [sys.executable, str(example_dir / "main.py")],
        cwd=repository_root,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip().endswith("Hello, World!")

    reflection_script = f"""
from jvm.config import Config
from jvm.loader import JVMLoader
from jvm.proxy import ClassProxy

config = Config.from_pyproject({str(example_dir)!r})
runtime = JVMLoader(config).start()
class_info = runtime.find_class("mypkg/Hello")
greet = next(method for method in class_info.methods if method.name == "greet")
assert greet.descriptor == "(Ljava/lang/String;)Ljava/lang/String;"
assert greet.method_id
assert ClassProxy(runtime, "mypkg.Hello").greet("JNI") == "Hello, JNI!"
print(greet.descriptor)
"""
    reflected = subprocess.run(
        [sys.executable, "-c", reflection_script],
        cwd=repository_root,
        check=False,
        capture_output=True,
        text=True,
    )

    assert reflected.returncode == 0, reflected.stderr
    assert reflected.stdout.strip().endswith("(Ljava/lang/String;)Ljava/lang/String;")


def test_selected_custom_package_stub_generation(temp_directory: Path) -> None:
    repository_root = Path(__file__).resolve().parents[1]
    example_dir = repository_root / "examples" / "hello"
    config = Config.from_pyproject(str(example_dir))

    try:
        JVMLoader(config)._find_libjvm(config.java_version)
    except RuntimeError:
        pytest.skip("Java 21 is not available for the hello example")

    script = f"""
from pathlib import Path
from jvm.cli import StubFileManager

output_dir = Path({str(temp_directory)!r})
StubFileManager().generate_stubs(output_dir, ["mypkg"])
stub = output_dir / "mypkg.pyi"
assert stub.exists()
content = stub.read_text()
assert "class Hello:" in content
assert "def greet(x: str) -> str: ..." in content
assert "-> Class" not in content
print(stub)
"""
    completed = subprocess.run(
        [sys.executable, "-c", script],
        cwd=example_dir,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip().endswith("mypkg.pyi")
