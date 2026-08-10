"""Tests for classpath package and class indexing."""

import zipfile
from pathlib import Path

import pytest

from jvm.classpath import ClasspathError, ClasspathIndex


def test_index_jar_packages_and_classes(temp_directory: Path) -> None:
    jar_path = temp_directory / "library.jar"
    with zipfile.ZipFile(jar_path, "w") as jar:
        jar.writestr("mypkg/Hello.class", b"")
        jar.writestr("mypkg/internal/Helper.class", b"")
        jar.writestr("mypkg/Hello$Nested.class", b"")
        jar.writestr("META-INF/MANIFEST.MF", b"")
        jar.writestr("module-info.class", b"")

    index = ClasspathIndex.from_entries([str(jar_path)])

    assert index.classes == frozenset({"mypkg.Hello", "mypkg.internal.Helper"})
    assert index.packages == frozenset({"mypkg", "mypkg.internal"})
    assert index.contains_package("mypkg")
    assert index.contains_class("mypkg.Hello")


def test_index_class_directory(temp_directory: Path) -> None:
    class_file = temp_directory / "com" / "example" / "Library.class"
    class_file.parent.mkdir(parents=True)
    class_file.touch()

    index = ClasspathIndex.from_entries([str(temp_directory)])

    assert index.contains_package("com")
    assert index.contains_package("com.example")
    assert index.contains_class("com.example.Library")


def test_index_rejects_unsupported_file(temp_directory: Path) -> None:
    text_file = temp_directory / "classes.txt"
    text_file.touch()

    with pytest.raises(ClasspathError, match="Unsupported classpath entry"):
        ClasspathIndex.from_entries([str(text_file)])
