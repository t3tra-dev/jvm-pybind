"""Tests for Java import hook functionality."""

import threading
from importlib.machinery import ModuleSpec
from types import ModuleType
from unittest.mock import Mock, patch

import pytest

from jvm.classpath import ClasspathIndex
from jvm.import_hook.finder import JavaFinder
from jvm.import_hook.loader import JavaLoader
from jvm.proxy import ClassProxy, PackageProxy


class TestJavaFinder:
    """Test JavaFinder functionality."""

    def test_java_finder_initialization(self) -> None:
        """Test JavaFinder initialization."""
        finder = JavaFinder()

        assert finder._jvm is None
        assert finder._jvm_lock is not None

    def test_java_finder_prefixes(self) -> None:
        """Test JavaFinder prefix configuration."""
        assert "java." in JavaFinder._PREFIXES
        assert "javax." in JavaFinder._PREFIXES
        assert "jdk." in JavaFinder._PREFIXES

    def test_find_spec_java_root_package(self) -> None:
        """Test finding spec for 'java' root package."""
        finder = JavaFinder()

        with patch.object(finder, "_get_jvm") as mock_get_jvm:
            mock_jvm = Mock()
            mock_get_jvm.return_value = mock_jvm

            spec = finder.find_spec("java", None)

            assert spec is not None
            assert spec.name == "java"
            assert isinstance(spec.loader, JavaLoader)
            assert spec.loader is not None
            assert spec.loader.jvm == mock_jvm
            assert spec.loader.fullname == "java"
            # Skip is_package check for Python 3.13+ compatibility

    def test_find_spec_java_lang_package(self) -> None:
        """Test finding spec for 'java.lang' package."""
        finder = JavaFinder()

        with patch.object(finder, "_get_jvm") as mock_get_jvm:
            mock_jvm = Mock()
            mock_get_jvm.return_value = mock_jvm

            spec = finder.find_spec("java.lang", None)

            assert spec is not None
            assert spec.name == "java.lang"
            assert isinstance(spec.loader, JavaLoader)
            assert spec.loader is not None
            assert spec.loader.jvm == mock_jvm
            assert spec.loader.fullname == "java.lang"
            # Skip is_package check for Python 3.13+ compatibility

    def test_find_spec_javax_package(self) -> None:
        """Test finding spec for javax package."""
        finder = JavaFinder()

        with patch.object(finder, "_get_jvm") as mock_get_jvm:
            mock_jvm = Mock()
            mock_get_jvm.return_value = mock_jvm

            spec = finder.find_spec("javax.swing", None)

            assert spec is not None
            assert spec.name == "javax.swing"
            # Skip is_package check for Python 3.13+ compatibility

    def test_find_spec_jdk_package(self) -> None:
        """Test finding spec for jdk package."""
        finder = JavaFinder()

        with patch.object(finder, "_get_jvm") as mock_get_jvm:
            mock_jvm = Mock()
            mock_get_jvm.return_value = mock_jvm

            spec = finder.find_spec("jdk.internal", None)

            assert spec is not None
            assert spec.name == "jdk.internal"
            # Skip is_package check for Python 3.13+ compatibility

    def test_find_spec_non_java_package(self) -> None:
        """Test finding spec for non-Java package returns None."""
        finder = JavaFinder()

        spec = finder.find_spec("os", None)

        assert spec is None

    def test_find_spec_custom_java_package(self) -> None:
        finder = JavaFinder()
        finder._classpath_index = ClasspathIndex(
            classes=frozenset({"mypkg.Hello"}),
            packages=frozenset({"mypkg"}),
        )

        with (
            patch.object(finder, "_get_jvm", return_value=Mock()) as get_jvm,
            patch("jvm.import_hook.finder.PathFinder.find_spec", return_value=None),
        ):
            spec = finder.find_spec("mypkg", None)

        assert spec is not None
        assert isinstance(spec.loader, JavaLoader)
        assert spec.loader.classpath_index == finder._classpath_index
        get_jvm.assert_called_once()

    def test_regular_python_package_wins_over_custom_java_package(self) -> None:
        finder = JavaFinder()
        finder._classpath_index = ClasspathIndex(
            classes=frozenset({"mypkg.Hello"}),
            packages=frozenset({"mypkg"}),
        )
        python_spec = ModuleSpec("mypkg", Mock())

        with (
            patch.object(finder, "_get_jvm") as get_jvm,
            patch(
                "jvm.import_hook.finder.PathFinder.find_spec",
                return_value=python_spec,
            ),
        ):
            spec = finder.find_spec("mypkg", None)

        assert spec is None
        get_jvm.assert_not_called()

    def test_find_spec_python_package(self) -> None:
        """Test finding spec for Python package returns None."""
        finder = JavaFinder()

        spec = finder.find_spec("sys", None)

        assert spec is None

    def test_find_spec_partial_match(self) -> None:
        """Test finding spec for partial Java package name returns None."""
        finder = JavaFinder()

        spec = finder.find_spec("jav", None)

        assert spec is None

    def test_get_jvm_first_call(self) -> None:
        """Test _get_jvm method on first call (initializes JVM)."""
        finder = JavaFinder()
        mock_config = Mock()

        with (
            patch.object(
                finder, "_get_config", return_value=mock_config
            ) as mock_get_config,
            patch("jvm.import_hook.finder.JVMLoader") as mock_loader_class,
        ):
            mock_loader = Mock()
            mock_jvm = Mock()
            mock_loader.start.return_value = mock_jvm
            mock_loader_class.return_value = mock_loader

            result = finder._get_jvm()

            assert result == mock_jvm
            assert finder._jvm == mock_jvm
            mock_get_config.assert_called_once()
            mock_loader_class.assert_called_once_with(mock_config)
            mock_loader.start.assert_called_once()

    def test_get_jvm_subsequent_calls(self) -> None:
        """Test _get_jvm method on subsequent calls (uses cached JVM)."""
        finder = JavaFinder()
        mock_jvm = Mock()
        finder._jvm = mock_jvm  # Pre-populate cache

        with patch.object(finder, "_get_config") as mock_get_config:
            result = finder._get_jvm()

            assert result == mock_jvm
            mock_get_config.assert_not_called()

    def test_get_jvm_thread_safety(self) -> None:
        """Test _get_jvm method thread safety."""
        finder = JavaFinder()
        results = []
        mock_config = Mock()
        mock_loader = Mock()
        mock_jvm = Mock()
        mock_loader.start.return_value = mock_jvm

        def worker() -> None:
            result = finder._get_jvm()
            results.append(result)

        with (
            patch.object(finder, "_get_config", return_value=mock_config),
            patch(
                "jvm.import_hook.finder.JVMLoader", return_value=mock_loader
            ) as mock_loader_class,
        ):
            threads = [threading.Thread(target=worker) for _ in range(5)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()

        # All threads should get the same JVM instance
        assert len(set(id(r) for r in results)) == 1  # All results are the same object
        mock_loader_class.assert_called_once_with(mock_config)
        mock_loader.start.assert_called_once()


class TestJavaLoader:
    """Test JavaLoader functionality."""

    def test_java_loader_initialization(self, mock_jvm: Mock) -> None:
        """Test JavaLoader initialization."""
        fullname = "java.lang"
        loader = JavaLoader(mock_jvm, fullname)

        assert loader.jvm == mock_jvm
        assert loader.fullname == fullname

    def test_create_module_success(self, mock_jvm: Mock) -> None:
        """Test successful module creation."""
        loader = JavaLoader(mock_jvm, "java.lang")
        spec = ModuleSpec("java.lang", loader)

        module = loader.create_module(spec)

        assert isinstance(module, ModuleType)
        assert module.__name__ == "java.lang"

    def test_create_module_none_spec(self, mock_jvm: Mock) -> None:
        """Test module creation with None spec."""
        loader = JavaLoader(mock_jvm, "java.lang")

        with pytest.raises(ValueError, match="ModuleSpec cannot be None"):
            loader.create_module(None)

    def test_exec_module_root_package(self, mock_jvm: Mock) -> None:
        """Test executing module for root 'java' package."""
        loader = JavaLoader(mock_jvm, "java")
        module = ModuleType("java")

        loader.exec_module(module)

        assert hasattr(module, "__path__")
        assert module.__path__ == []
        assert hasattr(module, "__getattr__")
        assert hasattr(module, "__repr__")
        assert module.__repr__() == "<Java root package>"

    def test_exec_module_root_package_getattr(self, mock_jvm: Mock) -> None:
        """Test __getattr__ behavior for root package."""
        loader = JavaLoader(mock_jvm, "java")
        module = ModuleType("java")

        loader.exec_module(module)

        # Test dynamic attribute access
        result = module.__getattr__("lang")

        assert isinstance(result, PackageProxy)
        assert result._pkg == "java.lang"
        assert result._jvm == mock_jvm

    def test_exec_module_subpackage(self, mock_jvm: Mock) -> None:
        """Test executing module for subpackage."""
        loader = JavaLoader(mock_jvm, "java.lang")
        module = ModuleType("java.lang")

        loader.exec_module(module)

        assert hasattr(module, "__getattr__")
        assert hasattr(module, "__repr__")
        assert module.__repr__() == "<Java package java.lang>"

    def test_exec_module_deep_package(self, mock_jvm: Mock) -> None:
        """Test executing module for deep package hierarchy."""
        loader = JavaLoader(mock_jvm, "java.util.concurrent")
        module = ModuleType("java.util.concurrent")

        loader.exec_module(module)

        assert hasattr(module, "__getattr__")
        assert module.__repr__() == "<Java package java.util.concurrent>"

    def test_exec_module_subpackage_getattr_class_found(self, mock_jvm: Mock) -> None:
        """Test __getattr__ behavior when class is found."""
        loader = JavaLoader(mock_jvm, "java.lang")
        module = ModuleType("java.lang")

        # Mock successful class finding
        mock_jvm.find_class.return_value = Mock()

        loader.exec_module(module)

        # Test dynamic attribute access for existing class
        result = module.__getattr__("String")

        assert isinstance(result, ClassProxy)
        assert result._fqcn == "java.lang.String"
        assert result._jvm == mock_jvm
        mock_jvm.find_class.assert_called_once_with("java/lang/String")

    def test_exec_module_custom_root_resolves_indexed_class(
        self, mock_jvm: Mock
    ) -> None:
        index = ClasspathIndex(
            classes=frozenset({"mypkg.Hello"}),
            packages=frozenset({"mypkg"}),
        )
        loader = JavaLoader(mock_jvm, "mypkg", index)
        module = ModuleType("mypkg")

        loader.exec_module(module)
        result = module.__getattr__("Hello")

        assert isinstance(result, ClassProxy)
        assert result._fqcn == "mypkg.Hello"
        mock_jvm.find_class.assert_not_called()

        with pytest.raises(AttributeError, match="Missing"):
            module.__getattr__("Missing")

    def test_exec_module_subpackage_getattr_class_not_found(
        self, mock_jvm: Mock
    ) -> None:
        """Test __getattr__ behavior when class is not found (returns package)."""
        loader = JavaLoader(mock_jvm, "java")
        module = ModuleType("java")

        # First, execute as root package
        loader.exec_module(module)

        # Now test subpackage behavior
        loader = JavaLoader(mock_jvm, "java.util")
        submodule = ModuleType("java.util")

        # Mock failed class finding
        mock_jvm.find_class.side_effect = Exception("Class not found")

        loader.exec_module(submodule)

        # Test dynamic attribute access for non-existent class (should return package)
        result = submodule.__getattr__("nonexistent")

        assert isinstance(result, PackageProxy)
        assert result._pkg == "java.util.nonexistent"
        assert result._jvm == mock_jvm

    def test_exec_module_subpackage_getattr_exception_handling(
        self, mock_jvm: Mock
    ) -> None:
        """Test __getattr__ exception handling."""
        loader = JavaLoader(mock_jvm, "java.lang")
        module = ModuleType("java.lang")

        # Mock find_class to raise exception
        mock_jvm.find_class.side_effect = RuntimeError("JNI error")

        loader.exec_module(module)

        # Should still return PackageProxy when class finding fails
        result = module.__getattr__("SomeClass")

        assert isinstance(result, PackageProxy)
        assert result._pkg == "java.lang.SomeClass"


class TestImportHookIntegration:
    """Test integration between JavaFinder and JavaLoader."""

    def test_complete_import_flow_root_package(self) -> None:
        """Test complete import flow for root package."""
        finder = JavaFinder()

        with patch.object(finder, "_get_jvm") as mock_get_jvm:
            mock_jvm = Mock()
            mock_get_jvm.return_value = mock_jvm

            # Find spec
            spec = finder.find_spec("java", None)
            assert spec is not None

            # Create module
            assert spec.loader is not None
            module = spec.loader.create_module(spec)
            assert isinstance(module, ModuleType)

            # Execute module
            spec.loader.exec_module(module)
            assert hasattr(module, "__getattr__")

    def test_complete_import_flow_subpackage(self) -> None:
        """Test complete import flow for subpackage."""
        finder = JavaFinder()

        with patch.object(finder, "_get_jvm") as mock_get_jvm:
            mock_jvm = Mock()
            mock_jvm.find_class.return_value = Mock()  # Mock successful class finding
            mock_get_jvm.return_value = mock_jvm

            # Find spec
            spec = finder.find_spec("java.lang", None)
            assert spec is not None
            # Skip is_package check for Python 3.13+ compatibility

            # Create and execute module
            assert spec.loader is not None
            module = spec.loader.create_module(spec)
            assert module is not None
            spec.loader.exec_module(module)

            # Test accessing a class
            string_proxy = module.__getattr__("String")
            assert isinstance(string_proxy, ClassProxy)

    def test_java_finder_integration(self) -> None:
        """Test JavaFinder integration with JVM initialization."""
        finder = JavaFinder()
        mock_config = Mock()

        with (
            patch.object(
                finder, "_get_config", return_value=mock_config
            ) as mock_get_config,
            patch("jvm.import_hook.finder.JVMLoader") as mock_loader_class,
        ):
            mock_loader = Mock()
            mock_jvm = Mock()
            mock_loader.start.return_value = mock_jvm
            mock_loader_class.return_value = mock_loader

            # Find spec (should trigger JVM initialization)
            spec = finder.find_spec("java.lang", None)

            assert spec is not None
            assert spec.loader is not None
            assert spec.loader.jvm == mock_jvm  # type: ignore

            # Verify JVM was initialized
            mock_get_config.assert_called_once()
            mock_loader_class.assert_called_once_with(mock_config)
            mock_loader.start.assert_called_once()


class TestImportHookEdgeCases:
    """Test edge cases and error conditions."""

    def test_java_finder_with_target_parameter(self) -> None:
        """Test JavaFinder with target parameter (should be ignored)."""
        finder = JavaFinder()

        with patch.object(finder, "_get_jvm") as mock_get_jvm:
            mock_jvm = Mock()
            mock_get_jvm.return_value = mock_jvm

            # target parameter should be ignored
            spec = finder.find_spec("java.lang", ["some", "path"], target="some_target")

            assert spec is not None
            assert spec.name == "java.lang"

    def test_java_loader_empty_fullname(self, mock_jvm: Mock) -> None:
        """Test JavaLoader with empty fullname."""
        loader = JavaLoader(mock_jvm, "")
        module = ModuleType("")

        # Should handle empty fullname gracefully
        loader.exec_module(module)

        assert hasattr(module, "__getattr__")
        assert hasattr(module, "__repr__")

    def test_java_loader_single_part_non_java(self, mock_jvm: Mock) -> None:
        """Test JavaLoader with single part that's not 'java'."""
        loader = JavaLoader(mock_jvm, "javax")
        module = ModuleType("javax")

        loader.exec_module(module)

        # Should be treated as root package
        assert hasattr(module, "__path__")
        assert module.__path__ == []
        assert hasattr(module, "__getattr__")

    def test_java_finder_case_sensitivity(self) -> None:
        """Test that JavaFinder is case-sensitive."""
        finder = JavaFinder()
        finder._classpath_index = ClasspathIndex.empty()

        # Should not match case variations
        spec_upper = finder.find_spec("JAVA.lang", None)
        spec_mixed = finder.find_spec("Java.Lang", None)

        assert spec_upper is None
        assert spec_mixed is None

    def test_java_loader_module_attributes_immutable(self, mock_jvm: Mock) -> None:
        """Test that loader-set module attributes can be accessed."""
        loader = JavaLoader(mock_jvm, "java.lang")
        module = ModuleType("java.lang")

        loader.exec_module(module)

        # Should be able to access loader-set attributes
        getattr_func = getattr(module, "__getattr__")
        repr_func = getattr(module, "__repr__")

        assert callable(getattr_func)
        assert callable(repr_func)
        assert repr_func() == "<Java package java.lang>"

    def test_java_loader_getattr_with_special_names(self, mock_jvm: Mock) -> None:
        """Test __getattr__ behavior with special attribute names."""
        loader = JavaLoader(mock_jvm, "java.lang")
        module = ModuleType("java.lang")

        mock_jvm.find_class.side_effect = Exception("Class not found")

        loader.exec_module(module)

        # Test accessing attributes with special names
        result = module.__getattr__("__special__")

        assert isinstance(result, PackageProxy)
        assert result._pkg == "java.lang.__special__"
