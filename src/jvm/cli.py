from __future__ import annotations

import argparse
import keyword
import os
import platform
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Optional

from .config import Config
from .loader import JVMLoader
from .logger import logger
from .stubgen import PyiStubGenerator

# 定数定義
STUB_PACKAGES = [
    "java.lang",
    "java.util",
    "java.io",
]
TEMP_STUBS_DIR_NAME = "temp_stubs"
PACKAGE_STUBS_DIR_NAME = "package_stubs"
JAVA_PACKAGE_NAME = "java"


def parse_stub_packages(value: str) -> list[str]:
    """Parse a comma-separated list of Python-importable Java packages."""
    packages: list[str] = []
    seen: set[str] = set()

    for raw_package in value.split(","):
        package = raw_package.strip()
        parts = package.split(".")
        if not package or any(
            not part.isidentifier() or keyword.iskeyword(part) for part in parts
        ):
            raise argparse.ArgumentTypeError(
                f"Invalid Java package name: {raw_package!r}"
            )
        if package not in seen:
            seen.add(package)
            packages.append(package)

    return packages


class VirtualEnvironmentDetector:
    """仮想環境検出"""

    def __init__(self) -> None:
        self.system = platform.system().lower()

    def detect_venv(self) -> Optional[Path]:
        """仮想環境検出"""
        venv_path = self._get_venv_path()
        if not venv_path:
            return None

        return self._get_site_packages_path(venv_path)

    def _get_venv_path(self) -> Optional[Path]:
        """仮想環境パス取得"""
        if "VIRTUAL_ENV" in os.environ:
            return Path(os.environ["VIRTUAL_ENV"])

        if hasattr(sys, "real_prefix") or (
            hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix
        ):
            return Path(sys.prefix)

        return None

    def _get_site_packages_path(self, venv_path: Path) -> Optional[Path]:
        """site-packagesパス構築"""
        if self.system == "windows":
            site_packages = venv_path / "Lib" / "site-packages"
        else:
            python_version = f"python{sys.version_info.major}.{sys.version_info.minor}"
            site_packages = venv_path / "lib" / python_version / "site-packages"

        return site_packages if site_packages.exists() else None


class StubFileManager:
    """スタブファイル管理"""

    def __init__(self) -> None:
        self.system = platform.system().lower()

    def get_stub_source_dir(self) -> Path:
        """スタブソースディレクトリ取得"""
        pyproject_path = Config._find_pyproject_toml()
        if pyproject_path:
            project_root = pyproject_path.parent
            package_stubs_dir = project_root / PACKAGE_STUBS_DIR_NAME
            if package_stubs_dir.exists():
                return package_stubs_dir

        fallback_dir = Path.cwd() / PACKAGE_STUBS_DIR_NAME
        if fallback_dir.exists():
            return fallback_dir

        raise FileNotFoundError("Could not find package_stubs directory")

    def generate_stubs(
        self, output_dir: Path, packages: Optional[list[str]] = None
    ) -> None:
        """スタブファイル生成"""
        logger.info("Generating fresh stub files...")

        config = Config.from_pyproject()
        jvm = JVMLoader(config).start()
        generator = PyiStubGenerator(jvm, str(output_dir))

        selected_packages = STUB_PACKAGES if packages is None else packages
        for package in selected_packages:
            self._generate_package_stub(generator, package)

    def _generate_package_stub(self, generator: PyiStubGenerator, package: str) -> None:
        """パッケージスタブ生成"""
        try:
            stub_file = generator.generate_package_stub(package)
            logger.info(f"Generated stub for {package}: {stub_file}")
        except Exception as e:
            logger.warning(f"Failed to generate stub for {package}: {e}")

    def copy_stubs_to_site_packages(
        self, stubs_source: Path, site_packages: Path
    ) -> bool:
        """スタブファイルコピー"""
        success = True

        for stub_file in stubs_source.rglob("*.pyi"):
            rel_path = stub_file.relative_to(stubs_source)
            target_file = site_packages / rel_path

            try:
                target_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(stub_file, target_file)
                logger.info(f"Installed: {rel_path}")
            except Exception as e:
                logger.error(f"Failed to install {rel_path}: {e}")
                success = False

        return success

    def cleanup_temp_directory(self, temp_dir: Path) -> None:
        """一時ディレクトリクリーンアップ"""
        if temp_dir.exists():
            shutil.rmtree(temp_dir)


class StubInstaller:
    """スタブインストーラー"""

    def __init__(self) -> None:
        self.venv_detector = VirtualEnvironmentDetector()
        self.file_manager = StubFileManager()

    def install_stubs(
        self,
        force_regenerate: bool = False,
        packages: Optional[list[str]] = None,
    ) -> bool:
        """スタブファイルインストール"""
        site_packages = self.venv_detector.detect_venv()
        if not site_packages:
            self._log_venv_error()
            return False

        logger.info(f"Installing stubs to: {site_packages}")

        stubs_source, temp_dir = self._get_stub_source(force_regenerate, packages)
        if not stubs_source:
            return False

        success = self.file_manager.copy_stubs_to_site_packages(
            stubs_source, site_packages
        )

        if temp_dir:
            self.file_manager.cleanup_temp_directory(temp_dir)

        self._log_installation_result(success)
        return success

    def _log_venv_error(self) -> None:
        """仮想環境エラー出力"""
        logger.error("Not running in a virtual environment.")
        logger.error("Please create and activate a virtual environment first:")
        logger.error("  python -m venv .venv")
        logger.error(
            "  source .venv/bin/activate  # On Windows: .venv\\Scripts\\activate"
        )

    def _get_stub_source(
        self,
        force_regenerate: bool,
        packages: Optional[list[str]] = None,
    ) -> tuple[Optional[Path], Optional[Path]]:
        """スタブソース取得"""
        temp_dir = None

        if force_regenerate or packages is not None:
            temp_dir = self._create_temp_stubs(packages)
            return temp_dir, temp_dir

        try:
            return self.file_manager.get_stub_source_dir(), None
        except FileNotFoundError as e:
            logger.warning(f"{e}")
            logger.info("Generating fresh stub files...")
            temp_dir = self._create_temp_stubs(packages)
            return temp_dir, temp_dir

    def _create_temp_stubs(self, packages: Optional[list[str]] = None) -> Path:
        """一時スタブディレクトリ作成"""
        temp_stubs_dir = Path(
            tempfile.mkdtemp(prefix=f"{TEMP_STUBS_DIR_NAME}-", dir=Path.cwd())
        )
        self.file_manager.generate_stubs(temp_stubs_dir, packages)
        return temp_stubs_dir

    def _log_installation_result(self, success: bool) -> None:
        """インストール結果出力"""
        if success:
            logger.info("✓ Stub installation completed successfully!")
        else:
            logger.error("✗ Some errors occurred during installation")

    def uninstall_stubs(self) -> bool:
        """スタブファイル削除"""
        site_packages = self.venv_detector.detect_venv()
        if not site_packages:
            logger.error("Not running in a virtual environment.")
            return False

        logger.info(f"Uninstalling stubs from: {site_packages}")

        java_dir = site_packages / JAVA_PACKAGE_NAME
        if java_dir.exists():
            try:
                shutil.rmtree(java_dir)
                logger.info("✓ Removed java package stubs")
            except Exception as e:
                logger.error(f"Failed to remove java directory: {e}")
                return False
        else:
            logger.info("No java stubs found to remove")

        logger.info("✓ Stub uninstallation completed!")
        return True

    def install_pth(self) -> bool:
        """JVM .pth ファイルインストール"""
        site_packages = self.venv_detector.detect_venv()
        if not site_packages:
            self._log_venv_error()
            return False

        pth_file = site_packages / "jvm.pth"
        logger.info(f"Installing jvm.pth to: {pth_file}")

        try:
            with open(pth_file, "w", encoding="utf-8") as f:
                f.write("import jvm\n")
            logger.info("✓ jvm.pth file installed successfully!")
            logger.info(
                "Now you can use 'from java.lang import System' directly in any Python script"
            )
            return True
        except Exception as e:
            logger.error(f"Failed to create jvm.pth file: {e}")
            return False


def create_parser() -> argparse.ArgumentParser:
    """Create command line argument parser"""
    parser = argparse.ArgumentParser(
        prog="jvm",
        description="JVM-PyBind: Python bindings for JVM with type stub management",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m jvm --install-stub="java.lang"       Install one package stub
  python -m jvm --install-stub="java.io,mypkg"  Install multiple package stubs
  python -m jvm --uninstall-stub   Remove JDK type stubs from virtual environment
  python -m jvm --install-pth      Install jvm.pth file to enable automatic JVM import
        """,
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--install-stub",
        nargs="?",
        const=STUB_PACKAGES,
        type=parse_stub_packages,
        metavar="PACKAGES",
        help=(
            "Install comma-separated Java package stubs; "
            "defaults to java.lang,java.util,java.io"
        ),
    )
    group.add_argument(
        "--uninstall-stub",
        action="store_true",
        help="Remove JDK type stubs from the current virtual environment",
    )
    group.add_argument(
        "--install-pth",
        action="store_true",
        help="Install jvm.pth file to enable automatic JVM import in virtual environment",
    )
    return parser


def main() -> int:
    """Main CLI entry point"""
    parser = create_parser()
    args = parser.parse_args()

    installer = StubInstaller()

    try:
        if args.install_stub is not None:
            success = installer.install_stubs(
                force_regenerate=False,
                packages=list(args.install_stub),
            )
        elif args.uninstall_stub:
            success = installer.uninstall_stubs()
        elif args.install_pth:
            success = installer.install_pth()
        else:
            parser.print_help()
            return 1

        return 0 if success else 1

    except KeyboardInterrupt:
        logger.info("\nOperation cancelled by user")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
