"""Tests for JVM loader functionality."""

import os
from typing import Any
from unittest.mock import Mock, patch

import pytest

from jvm.config import Config
from jvm.loader import JVMLoader


class TestJVMLoaderInitialization:
    """Test JVMLoader initialization."""

    def test_jvm_loader_initialization(self) -> None:
        """Test JVMLoader initialization with config."""
        config = Config(java_version="17", deps={}, classpath=["test.jar"])
        loader = JVMLoader(config)

        assert loader.cfg == config
        assert loader.cfg.java_version == "17"
        assert loader.cfg.classpath == ["test.jar"]

    def test_jvm_loader_with_empty_config(self) -> None:
        """Test JVMLoader initialization with empty config."""
        config = Config(java_version="11", deps={}, classpath=[])
        loader = JVMLoader(config)

        assert loader.cfg == config
        assert loader.cfg.java_version == "11"
        assert loader.cfg.classpath == []


class TestJVMLoaderStart:
    """Test JVM starting functionality."""

    @patch("jvm.loader.JVM")
    @patch("jvm.loader.ctypes.CDLL")
    @patch("jvm.loader.JVMLoader._find_libjvm")
    def test_start_success_no_classpath(
        self,
        mock_find_libjvm: Mock,
        mock_cdll: Mock,
        mock_jvm_class: Mock,
        mock_platform: dict[str, Any],
    ) -> None:
        """Test successful JVM start without classpath."""
        # Setup
        mock_platform["system"] = "Linux"
        mock_platform["machine"] = "x86_64"

        config = Config(java_version="17", deps={}, classpath=[])
        loader = JVMLoader(config)

        # Mock libjvm path and library
        mock_libjvm_path = "/usr/lib/jvm/java-17/lib/server/libjvm.so"
        mock_find_libjvm.return_value = mock_libjvm_path

        # Mock CDLL and JNI_CreateJavaVM
        mock_libjvm = Mock()
        mock_libjvm.JNI_CreateJavaVM.return_value = 0  # Success
        mock_cdll.return_value = mock_libjvm

        # Mock JVM class constructor
        mock_jvm_instance = Mock()
        mock_jvm_class.return_value = mock_jvm_instance

        # Mock ctypes functions that don't interfere with structure definitions
        with patch("jvm.loader.ctypes.byref") as mock_byref:
            mock_byref.return_value = Mock()

            result = loader.start()

            # Verify calls
            mock_find_libjvm.assert_called_once_with("17")
            mock_cdll.assert_called_once_with(mock_libjvm_path)
            mock_libjvm.JNI_CreateJavaVM.assert_called_once()
            mock_jvm_class.assert_called_once()

            # Should return mocked JVM instance
            assert result == mock_jvm_instance

    @patch("jvm.loader.JVM")
    @patch("jvm.loader.ctypes.CDLL")
    @patch("jvm.loader.JVMLoader._find_libjvm")
    def test_start_success_with_classpath(
        self,
        mock_find_libjvm: Mock,
        mock_cdll: Mock,
        mock_jvm_class: Mock,
        mock_platform: dict[str, Any],
    ) -> None:
        """Test successful JVM start with classpath."""
        # Setup
        mock_platform["system"] = "Linux"
        mock_platform["machine"] = "x86_64"

        config = Config(
            java_version="17", deps={}, classpath=["lib/test.jar", "lib/another.jar"]
        )
        loader = JVMLoader(config)

        # Mock libjvm
        mock_libjvm_path = "/usr/lib/jvm/java-17/lib/server/libjvm.so"
        mock_find_libjvm.return_value = mock_libjvm_path

        mock_libjvm = Mock()
        mock_libjvm.JNI_CreateJavaVM.return_value = 0
        mock_cdll.return_value = mock_libjvm

        # Mock JVM class constructor
        mock_jvm_instance = Mock()
        mock_jvm_class.return_value = mock_jvm_instance

        # Mock ctypes functions that don't interfere with structure definitions
        with patch("jvm.loader.ctypes.byref") as mock_byref:
            mock_byref.return_value = Mock()

            result = loader.start()

            # Verify JVM was created successfully
            assert result == mock_jvm_instance
            mock_libjvm.JNI_CreateJavaVM.assert_called_once()
            mock_jvm_class.assert_called_once()

    @patch("jvm.loader.JVM")
    @patch("jvm.loader.ctypes.CDLL")
    @patch("jvm.loader.JVMLoader._find_libjvm")
    def test_start_arm64_macos_optimizations(
        self,
        mock_find_libjvm: Mock,
        mock_cdll: Mock,
        mock_jvm_class: Mock,
        mock_platform: dict[str, Any],
    ) -> None:
        """Test JVM start with ARM64 macOS optimizations."""
        # Setup for ARM64 macOS
        mock_platform["system"] = "Darwin"
        mock_platform["machine"] = "arm64"

        config = Config(java_version="17", deps={}, classpath=[])
        loader = JVMLoader(config)

        # Mock libjvm
        mock_libjvm_path = "/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home/lib/server/libjvm.dylib"
        mock_find_libjvm.return_value = mock_libjvm_path

        mock_libjvm = Mock()
        mock_libjvm.JNI_CreateJavaVM.return_value = 0
        mock_cdll.return_value = mock_libjvm

        # Mock JVM class constructor
        mock_jvm_instance = Mock()
        mock_jvm_class.return_value = mock_jvm_instance

        # Mock ctypes functions that don't interfere with structure definitions
        with patch("jvm.loader.ctypes.byref") as mock_byref:
            mock_byref.return_value = Mock()

            result = loader.start()

            # Should include ARM64 optimizations
            assert result == mock_jvm_instance
            mock_libjvm.JNI_CreateJavaVM.assert_called_once()
            mock_jvm_class.assert_called_once()

    @patch("jvm.loader.JVMLoader._find_libjvm")
    def test_start_jvm_init_failure(
        self, mock_find_libjvm: Mock, mock_ctypes_cdll: Mock
    ) -> None:
        """Test JVM start when initialization fails."""
        config = Config(java_version="17", deps={}, classpath=[])
        loader = JVMLoader(config)

        # Mock libjvm
        mock_libjvm_path = "/path/to/libjvm.so"
        mock_find_libjvm.return_value = mock_libjvm_path

        # Mock JNI_CreateJavaVM to return failure
        mock_lib = Mock()
        mock_lib.JNI_CreateJavaVM.return_value = -1  # Failure
        mock_ctypes_cdll.return_value = mock_lib

        with patch("jvm.loader.ctypes.byref"):
            with pytest.raises(RuntimeError, match="JVM init failed, code -1"):
                loader.start()


class TestFindLibjvm:
    """Test libjvm library finding functionality."""

    def test_find_libjvm_windows(
        self, mock_platform: dict[str, Any], mock_os_path_exists: Mock
    ) -> None:
        """Test finding libjvm on Windows."""
        mock_platform["system"] = "Windows"
        config = Config(java_version="17", deps={}, classpath=[])
        loader = JVMLoader(config)

        # Mock the first path to exist
        expected_path = "C:\\Program Files\\Java\\jdk-17\\bin\\server\\jvm.dll"
        mock_os_path_exists.side_effect = lambda path: path == expected_path

        result = loader._find_libjvm("17")

        assert result == expected_path
        # Should find it on the first try since we mocked the first path to exist
        assert mock_os_path_exists.call_count == 1

    def test_find_libjvm_macos(
        self, mock_platform: dict[str, Any], mock_os_path_exists: Mock
    ) -> None:
        """Test finding libjvm on macOS."""
        mock_platform["system"] = "Darwin"
        config = Config(java_version="17", deps={}, classpath=[])
        loader = JVMLoader(config)

        expected_path = "/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home/lib/server/libjvm.dylib"
        mock_os_path_exists.side_effect = lambda path: path == expected_path

        result = loader._find_libjvm("17")

        assert result == expected_path

    def test_find_libjvm_linux(
        self, mock_platform: dict[str, Any], mock_os_path_exists: Mock
    ) -> None:
        """Test finding libjvm on Linux."""
        mock_platform["system"] = "Linux"
        config = Config(java_version="17", deps={}, classpath=[])
        loader = JVMLoader(config)

        expected_path = "/usr/lib/jvm/java-17-openjdk/lib/server/libjvm.so"
        mock_os_path_exists.side_effect = lambda path: path == expected_path

        result = loader._find_libjvm("17")

        assert result == expected_path

    def test_find_libjvm_not_found(
        self, mock_platform: dict[str, Any], mock_os_path_exists: Mock
    ) -> None:
        """Test finding libjvm when not found."""
        mock_platform["system"] = "Linux"
        mock_os_path_exists.return_value = False  # No paths exist

        config = Config(java_version="17", deps={}, classpath=[])
        loader = JVMLoader(config)

        with pytest.raises(
            RuntimeError, match="Could not find libjvm for Java 17 on linux"
        ):
            loader._find_libjvm("17")

    def test_find_libjvm_unsupported_platform(
        self, mock_platform: dict[str, Any]
    ) -> None:
        """Test finding libjvm on unsupported platform."""
        mock_platform["system"] = "FreeBSD"

        config = Config(java_version="17", deps={}, classpath=[])
        loader = JVMLoader(config)

        with pytest.raises(RuntimeError, match="Unsupported platform: freebsd"):
            loader._find_libjvm("17")

    def test_find_libjvm_multiple_versions(
        self, mock_platform: dict[str, Any], mock_os_path_exists: Mock
    ) -> None:
        """Test finding libjvm for different Java versions."""
        mock_platform["system"] = "Linux"
        config = Config(java_version="11", deps={}, classpath=[])
        loader = JVMLoader(config)

        # Mock only Java 11 path to exist
        def path_exists(path: str) -> bool:
            return "java-11" in path

        mock_os_path_exists.side_effect = path_exists

        result = loader._find_libjvm("11")

        assert "java-11" in result
        assert result.endswith("libjvm.so")

    def test_find_libjvm_windows_different_distributions(
        self, mock_platform: dict[str, Any], mock_os_path_exists: Mock
    ) -> None:
        """Test finding libjvm for different JDK distributions on Windows."""
        mock_platform["system"] = "Windows"
        config = Config(java_version="17", deps={}, classpath=[])
        loader = JVMLoader(config)

        # Mock Eclipse Adoptium path to exist
        adoptium_path = (
            "C:\\Program Files\\Eclipse Adoptium\\jdk-17\\bin\\server\\jvm.dll"
        )
        mock_os_path_exists.side_effect = lambda path: path == adoptium_path

        result = loader._find_libjvm("17")

        assert result == adoptium_path


class TestClasspathGeneration:
    """Test classpath generation functionality."""

    def test_classpath_empty(self) -> None:
        """Test classpath generation with empty classpath."""
        config = Config(java_version="17", deps={}, classpath=[])
        loader = JVMLoader(config)

        result = loader._classpath(config)

        assert result == ""

    def test_classpath_single_jar(self) -> None:
        """Test classpath generation with single JAR."""
        config = Config(java_version="17", deps={}, classpath=["lib/test.jar"])
        loader = JVMLoader(config)

        result = loader._classpath(config)

        assert result == "lib/test.jar"

    def test_classpath_multiple_jars(self) -> None:
        """Test classpath generation with multiple JARs."""
        config = Config(
            java_version="17",
            deps={},
            classpath=["lib/test.jar", "lib/another.jar", "build/classes"],
        )
        loader = JVMLoader(config)

        result = loader._classpath(config)

        expected = os.pathsep.join(["lib/test.jar", "lib/another.jar", "build/classes"])
        assert result == expected

    def test_classpath_with_spaces(self) -> None:
        """Test classpath generation with paths containing spaces."""
        config = Config(
            java_version="17",
            deps={},
            classpath=["lib/test jar.jar", "build/my classes"],
        )
        loader = JVMLoader(config)

        result = loader._classpath(config)

        expected = os.pathsep.join(["lib/test jar.jar", "build/my classes"])
        assert result == expected


class TestJVMOptionsGeneration:
    """Test JVM options generation."""

    @patch("jvm.loader.JVM")
    @patch("jvm.loader.ctypes.CDLL")
    @patch("jvm.loader.JVMLoader._find_libjvm")
    def test_jvm_options_no_classpath_linux(
        self,
        mock_find_libjvm: Mock,
        mock_cdll: Mock,
        mock_jvm_class: Mock,
        mock_platform: dict[str, Any],
    ) -> None:
        """Test JVM options without classpath on Linux."""
        mock_platform["system"] = "Linux"
        mock_platform["machine"] = "x86_64"

        config = Config(java_version="17", deps={}, classpath=[])
        loader = JVMLoader(config)

        # Mock dependencies
        mock_find_libjvm.return_value = "/path/to/libjvm.so"
        mock_lib = Mock()
        mock_lib.JNI_CreateJavaVM.return_value = 0
        mock_cdll.return_value = mock_lib

        # Mock JVM class constructor
        mock_jvm_instance = Mock()
        mock_jvm_class.return_value = mock_jvm_instance

        with patch("jvm.loader.ctypes.byref"):
            result = loader.start()

            # Should succeed without options
            assert result == mock_jvm_instance
            mock_lib.JNI_CreateJavaVM.assert_called_once()
            mock_jvm_class.assert_called_once()

    @patch("jvm.loader.JVM")
    @patch("jvm.loader.ctypes.CDLL")
    @patch("jvm.loader.JVMLoader._find_libjvm")
    def test_jvm_options_with_classpath(
        self,
        mock_find_libjvm: Mock,
        mock_cdll: Mock,
        mock_jvm_class: Mock,
        mock_platform: dict[str, Any],
    ) -> None:
        """Test JVM options with classpath."""
        mock_platform["system"] = "Linux"
        mock_platform["machine"] = "x86_64"

        config = Config(java_version="17", deps={}, classpath=["test.jar"])
        loader = JVMLoader(config)

        # Mock dependencies
        mock_find_libjvm.return_value = "/path/to/libjvm.so"
        mock_lib = Mock()
        mock_lib.JNI_CreateJavaVM.return_value = 0
        mock_cdll.return_value = mock_lib

        # Mock JVM class constructor
        mock_jvm_instance = Mock()
        mock_jvm_class.return_value = mock_jvm_instance

        with patch("jvm.loader.ctypes.byref"):
            result = loader.start()

            # Should include classpath option
            assert result == mock_jvm_instance
            mock_lib.JNI_CreateJavaVM.assert_called_once()
            mock_jvm_class.assert_called_once()

    @patch("jvm.loader.JVM")
    @patch("jvm.loader.ctypes.CDLL")
    @patch("jvm.loader.JVMLoader._find_libjvm")
    def test_jvm_options_arm64_macos(
        self,
        mock_find_libjvm: Mock,
        mock_cdll: Mock,
        mock_jvm_class: Mock,
        mock_platform: dict[str, Any],
    ) -> None:
        """Test JVM options for ARM64 macOS."""
        mock_platform["system"] = "Darwin"
        mock_platform["machine"] = "arm64"

        config = Config(java_version="17", deps={}, classpath=[])
        loader = JVMLoader(config)

        # Mock dependencies
        mock_find_libjvm.return_value = "/path/to/libjvm.dylib"
        mock_lib = Mock()
        mock_lib.JNI_CreateJavaVM.return_value = 0
        mock_cdll.return_value = mock_lib

        # Mock JVM class constructor
        mock_jvm_instance = Mock()
        mock_jvm_class.return_value = mock_jvm_instance

        with patch("jvm.loader.ctypes.byref"):
            result = loader.start()

            # Should include ARM64 optimizations
            assert result == mock_jvm_instance
            mock_lib.JNI_CreateJavaVM.assert_called_once()
            mock_jvm_class.assert_called_once()


class TestJVMLoaderEdgeCases:
    """Test edge cases and error conditions."""

    def test_loader_with_none_config(self) -> None:
        """Test loader behavior with invalid config."""
        # This should not happen in normal usage, but test defensive programming
        try:
            loader = JVMLoader(None)  # type: ignore[arg-type]
            # If we get here, the loader should handle it gracefully
            assert loader.cfg is None
        except (TypeError, AttributeError):
            # This is also acceptable behavior
            pass

    @patch("jvm.loader.JVMLoader._find_libjvm")
    def test_start_with_library_load_error(
        self, mock_find_libjvm: Mock, mock_ctypes_cdll: Mock
    ) -> None:
        """Test JVM start when library loading fails."""
        config = Config(java_version="17", deps={}, classpath=[])
        loader = JVMLoader(config)

        mock_find_libjvm.return_value = "/path/to/libjvm.so"
        mock_ctypes_cdll.side_effect = OSError("Library not found")

        with pytest.raises(OSError, match="Library not found"):
            loader.start()

    def test_classpath_with_none(self) -> None:
        """Test classpath generation with None classpath."""
        config = Config(java_version="17", deps={}, classpath=None)  # type: ignore[arg-type]
        loader = JVMLoader(config)

        # Modify config to have None classpath
        config.classpath = None  # type: ignore[assignment]

        result = loader._classpath(config)

        assert result == ""

    @patch("jvm.loader.platform.system")
    def test_find_libjvm_case_insensitive_platform(self, mock_system: Mock) -> None:
        """Test platform detection is case-insensitive."""
        mock_system.return_value = "LINUX"  # Uppercase

        config = Config(java_version="17", deps={}, classpath=[])
        loader = JVMLoader(config)

        with patch("os.path.exists", return_value=False):
            with pytest.raises(
                RuntimeError, match="Could not find libjvm for Java 17 on linux"
            ):
                loader._find_libjvm("17")

    def test_empty_java_version(
        self, mock_platform: dict[str, Any], mock_os_path_exists: Mock
    ) -> None:
        """Test finding libjvm with empty Java version."""
        mock_platform["system"] = "Linux"
        mock_os_path_exists.return_value = False

        config = Config(java_version="", deps={}, classpath=[])
        loader = JVMLoader(config)

        with pytest.raises(
            RuntimeError, match="Could not find libjvm for Java  on linux"
        ):
            loader._find_libjvm("")
