"""Tests for CLI package-selective stub generation."""

from pathlib import Path
from unittest.mock import Mock, call, patch

import pytest

from jvm.cli import STUB_PACKAGES, StubFileManager, StubInstaller, create_parser, main
from jvm.stubgen import PyiStubGenerator


def test_install_stub_parses_one_package() -> None:
    args = create_parser().parse_args(["--install-stub=java.lang"])

    assert args.install_stub == ["java.lang"]


def test_install_stub_parses_multiple_packages() -> None:
    args = create_parser().parse_args(["--install-stub=java.io, mypkg,java.io"])

    assert args.install_stub == ["java.io", "mypkg"]


def test_install_stub_without_value_keeps_default_packages() -> None:
    args = create_parser().parse_args(["--install-stub"])

    assert args.install_stub == STUB_PACKAGES


@pytest.mark.parametrize(
    "value",
    ["", "java..lang", "../mypkg", "java.lang,", "class"],
)
def test_install_stub_rejects_invalid_package(value: str) -> None:
    with pytest.raises(SystemExit):
        create_parser().parse_args([f"--install-stub={value}"])


def test_stub_file_manager_generates_only_selected_packages(
    temp_directory: Path,
) -> None:
    config = Mock()
    runtime = Mock()
    generator = Mock()
    generator.generate_package_stub.side_effect = [
        temp_directory / "java" / "io.pyi",
        temp_directory / "mypkg.pyi",
    ]

    with (
        patch("jvm.cli.Config.from_pyproject", return_value=config),
        patch("jvm.cli.JVMLoader") as loader_class,
        patch("jvm.cli.PyiStubGenerator", return_value=generator),
    ):
        loader_class.return_value.start.return_value = runtime
        StubFileManager().generate_stubs(
            temp_directory,
            ["java.io", "mypkg"],
        )

    loader_class.assert_called_once_with(config)
    loader_class.return_value.start.assert_called_once()
    generator.generate_package_stub.assert_has_calls([call("java.io"), call("mypkg")])
    assert generator.generate_package_stub.call_count == 2


def test_main_passes_selected_packages_to_installer() -> None:
    installer = Mock()
    installer.install_stubs.return_value = True

    with (
        patch("sys.argv", ["jvm", "--install-stub=java.io,mypkg"]),
        patch("jvm.cli.StubInstaller", return_value=installer),
    ):
        result = main()

    assert result == 0
    installer.install_stubs.assert_called_once_with(
        force_regenerate=False,
        packages=["java.io", "mypkg"],
    )


def test_selected_packages_force_fresh_stub_generation(
    temp_directory: Path,
) -> None:
    installer = StubInstaller()
    site_packages = temp_directory / "site-packages"
    generated_stubs = temp_directory / "generated"
    site_packages.mkdir()
    generated_stubs.mkdir()
    installer.venv_detector.detect_venv = Mock(return_value=site_packages)
    installer._create_temp_stubs = Mock(return_value=generated_stubs)  # type: ignore[method-assign]
    installer.file_manager.copy_stubs_to_site_packages = Mock(return_value=True)  # type: ignore[method-assign]
    installer.file_manager.cleanup_temp_directory = Mock()  # type: ignore[method-assign]

    assert installer.install_stubs(packages=["mypkg"]) is True

    installer._create_temp_stubs.assert_called_once_with(["mypkg"])
    installer.file_manager.copy_stubs_to_site_packages.assert_called_once_with(
        generated_stubs,
        site_packages,
    )
    installer.file_manager.cleanup_temp_directory.assert_called_once_with(
        generated_stubs
    )


def test_package_stub_paths_follow_python_module_layout(
    temp_directory: Path,
) -> None:
    generator = PyiStubGenerator(Mock(), str(temp_directory))

    root_stub = generator.generate_package_stub("mypkg", class_names=[])
    nested_stub = generator.generate_package_stub("com.example", class_names=[])

    assert root_stub == temp_directory / "mypkg.pyi"
    assert nested_stub == temp_directory / "com" / "example.pyi"
    assert generator.java_type_to_python_type("java.lang.Class", "mypkg") == "Any"
