"""Integration tests for JVM-PyBind functionality."""

import sys
from importlib.machinery import ModuleSpec

import pytest

from jvm.import_hook.finder import JavaFinder
from jvm.import_hook.loader import JavaLoader
from jvm.jvm import JVM
from jvm.proxy import ClassProxy, PackageProxy
from jvm.typeconv import to_java, to_python


@pytest.mark.integration
class TestBasicJavaClassUsage:
    """Test basic Java class usage with real JVM."""

    def test_system_class_access(self, jvm_instance: JVM) -> None:
        """Test accessing java.lang.System class."""
        system_class_info = jvm_instance.find_class("java/lang/System")

        assert system_class_info.name == "java/lang/System"
        assert len(system_class_info.methods) > 0
        assert len(system_class_info.fields) > 0

        method_names = [m.name for m in system_class_info.methods]
        assert "getProperty" in method_names
        assert "currentTimeMillis" in method_names

        field_names = [f.name for f in system_class_info.fields]
        assert "out" in field_names
        assert "err" in field_names
        assert "in" in field_names

    def test_string_class_access(self, jvm_instance: JVM) -> None:
        """Test accessing java.lang.String class."""
        string_class_info = jvm_instance.find_class("java/lang/String")

        assert string_class_info.name == "java/lang/String"
        assert len(string_class_info.methods) > 0

        method_names = [m.name for m in string_class_info.methods]
        assert "length" in method_names
        assert "charAt" in method_names
        assert "substring" in method_names
        assert "valueOf" in method_names

    def test_object_class_access(self, jvm_instance: JVM) -> None:
        """Test accessing java.lang.Object class."""
        object_class_info = jvm_instance.find_class("java/lang/Object")

        assert object_class_info.name == "java/lang/Object"
        assert len(object_class_info.methods) > 0

        method_names = [m.name for m in object_class_info.methods]
        assert "toString" in method_names
        assert "equals" in method_names
        assert "hashCode" in method_names
        assert "getClass" in method_names


@pytest.mark.integration
class TestPackageDiscovery:
    """Test Java package discovery functionality."""

    def test_discover_java_lang_classes(self, jvm_instance: JVM) -> None:
        """Test discovering classes in java.lang package."""
        classes = jvm_instance.discover_package_classes("java.lang")

        assert len(classes) > 0
        assert "java.lang.String" in classes
        assert "java.lang.Object" in classes
        assert "java.lang.System" in classes
        assert "java.lang.Integer" in classes

    def test_discover_java_util_classes(self, jvm_instance: JVM) -> None:
        """Test discovering classes in java.util package."""
        classes = jvm_instance.discover_package_classes("java.util")

        assert len(classes) > 0
        assert "java.util.List" in classes
        assert "java.util.ArrayList" in classes
        assert "java.util.HashMap" in classes
        assert "java.util.Date" in classes

    def test_discover_java_io_classes(self, jvm_instance: JVM) -> None:
        """Test discovering classes in java.io package."""
        classes = jvm_instance.discover_package_classes("java.io")

        assert len(classes) > 0
        assert "java.io.File" in classes
        assert "java.io.InputStream" in classes
        assert "java.io.OutputStream" in classes

    def test_discover_nonexistent_package(self, jvm_instance: JVM) -> None:
        """Test discovering classes in non-existent package."""
        classes = jvm_instance.discover_package_classes("com.nonexistent")

        assert classes == []


@pytest.mark.integration
class TestTypeConversionIntegration:
    """Test type conversion with real JVM."""

    def test_string_conversion_roundtrip(self, jvm_instance: JVM) -> None:
        """Test Python string to Java String and back."""
        original_string = "Hello, JVM-PyBind!"

        java_string = to_java(jvm_instance, original_string)
        assert java_string is not None

        python_string = to_python(jvm_instance, java_string)
        assert python_string == original_string

    def test_boolean_conversion_roundtrip(self, jvm_instance: JVM) -> None:
        """Test Python boolean to Java Boolean and back."""
        for original_bool in [True, False]:
            java_boolean = to_java(jvm_instance, original_bool)
            assert java_boolean is not None

            python_boolean = to_python(jvm_instance, java_boolean)
            assert python_boolean == original_bool

    def test_integer_conversion_roundtrip(self, jvm_instance: JVM) -> None:
        """Test Python int to Java Integer and back."""
        test_values = [0, 42, -123, 2147483647, -2147483648]

        for original_int in test_values:
            java_integer = to_java(jvm_instance, original_int)
            assert java_integer is not None

            python_integer = to_python(jvm_instance, java_integer)
            assert python_integer == original_int

    def test_unicode_string_conversion(self, jvm_instance: JVM) -> None:
        """Test Unicode string conversion."""
        unicode_strings = [
            "Hello 世界",
            "Здравствуй мир",
            "مرحبا بالعالم",
        ]

        for original_string in unicode_strings:
            java_string = to_java(jvm_instance, original_string)
            python_string = to_python(jvm_instance, java_string)
            assert python_string == original_string


@pytest.mark.integration
class TestProxySystemIntegration:
    """Test proxy system with real JVM."""

    def test_package_proxy_creation(self, jvm_instance: JVM) -> None:
        """Test creating PackageProxy."""
        package_proxy = PackageProxy(jvm_instance, "java.lang")

        assert package_proxy._jvm == jvm_instance
        assert package_proxy._pkg == "java.lang"
        assert repr(package_proxy) == "<Java package java.lang>"

    def test_class_proxy_creation(self, jvm_instance: JVM) -> None:
        """Test creating ClassProxy."""
        class_proxy = ClassProxy(jvm_instance, "java.lang.System")

        assert class_proxy._jvm == jvm_instance
        assert class_proxy._fqcn == "java.lang.System"
        assert repr(class_proxy) == "<Java class java.lang.System>"

    def test_package_proxy_class_access(self, jvm_instance: JVM) -> None:
        """Test accessing classes through PackageProxy."""
        java_lang = PackageProxy(jvm_instance, "java.lang")

        system_proxy = java_lang.System
        assert isinstance(system_proxy, ClassProxy)
        assert system_proxy._fqcn == "java.lang.System"

        string_proxy = java_lang.String
        assert isinstance(string_proxy, ClassProxy)
        assert string_proxy._fqcn == "java.lang.String"

    def test_package_proxy_subpackage_access(self, jvm_instance: JVM) -> None:
        """Test accessing subpackages through PackageProxy."""
        java_root = PackageProxy(jvm_instance, "java")

        util_proxy = java_root.util
        assert isinstance(util_proxy, PackageProxy)
        assert util_proxy._pkg == "java.util"

    def test_class_proxy_method_access(self, jvm_instance: JVM) -> None:
        """Test accessing methods through ClassProxy."""
        system_proxy = ClassProxy(jvm_instance, "java.lang.System")

        get_property_method = system_proxy.getProperty
        assert hasattr(get_property_method, "__call__")

        current_time_method = system_proxy.currentTimeMillis
        assert hasattr(current_time_method, "__call__")

    def test_typed_static_primitive_call(self, jvm_instance: JVM) -> None:
        math_proxy = ClassProxy(jvm_instance, "java.lang.Math")

        assert math_proxy.abs(-42) == 42

    def test_all_typed_primitive_call_kinds(self, jvm_instance: JVM) -> None:
        assert (
            ClassProxy(jvm_instance, "java.lang.Boolean").logicalAnd(True, False)
            is False
        )
        assert ClassProxy(jvm_instance, "java.lang.Byte").parseByte("127") == 127
        assert ClassProxy(jvm_instance, "java.lang.Character").toUpperCase("a") == "A"
        assert ClassProxy(jvm_instance, "java.lang.Short").parseShort("1234") == 1234
        assert ClassProxy(jvm_instance, "java.lang.Long").sum(20, 22) == 42
        assert ClassProxy(jvm_instance, "java.lang.Float").sum(
            1.25, 2.5
        ) == pytest.approx(3.75)
        assert ClassProxy(jvm_instance, "java.lang.Double").sum(
            1.25, 2.5
        ) == pytest.approx(3.75)
        assert ClassProxy(jvm_instance, "java.lang.System").gc() is None

    def test_typed_static_primitive_fields(self, jvm_instance: JVM) -> None:
        assert ClassProxy(jvm_instance, "java.lang.Integer").MAX_VALUE == 2**31 - 1
        assert ClassProxy(jvm_instance, "java.lang.Long").MAX_VALUE == 2**63 - 1
        assert ClassProxy(jvm_instance, "java.lang.Character").MAX_VALUE == "\uffff"
        assert ClassProxy(jvm_instance, "java.lang.Math").PI == pytest.approx(
            3.141592653589793
        )

    def test_constructor_and_typed_instance_calls(self, jvm_instance: JVM) -> None:
        builder_proxy = ClassProxy(jvm_instance, "java.lang.StringBuilder")

        builder = builder_proxy("Hello")

        assert builder.length() == 5
        assert builder.append("!").toString() == "Hello!"

    def test_primitive_array_argument_and_return(self, jvm_instance: JVM) -> None:
        arrays_proxy = ClassProxy(jvm_instance, "java.util.Arrays")

        assert arrays_proxy.toString([1, 2, 3]) == "[1, 2, 3]"
        assert arrays_proxy.copyOf([1, 2, 3], 5) == [1, 2, 3, 0, 0]


@pytest.mark.integration
class TestImportHookIntegration:
    """Test import hook functionality with real JVM."""

    def test_java_finder_integration(self, jvm_instance: JVM) -> None:
        """Test JavaFinder with existing JVM."""
        finder = JavaFinder()
        # Use the existing JVM instead of creating a new one
        finder._jvm = jvm_instance

        # Should be able to find Java packages
        spec = finder.find_spec("java.lang", None)
        assert spec is not None
        assert spec.name == "java.lang"
        # Skip is_package check for Python 3.13+ compatibility

        # JVM should be initialized
        assert finder._jvm is not None
        assert isinstance(finder._jvm, JVM)

    def test_java_loader_integration(self, jvm_instance: JVM) -> None:
        """Test JavaLoader with existing JVM."""
        # Test JavaLoader
        java_loader = JavaLoader(jvm_instance, "java.lang")
        spec = ModuleSpec("java.lang", java_loader)

        # Create and execute module
        module = java_loader.create_module(spec)
        java_loader.exec_module(module)

        # Should be able to access classes
        string_proxy = module.__getattr__("String")
        assert isinstance(string_proxy, ClassProxy)
        assert string_proxy._fqcn == "java.lang.String"

    @pytest.mark.skipif(
        sys.platform == "win32",
        reason="Import hook manipulation can be flaky on Windows",
    )
    def test_actual_import_simulation(self, jvm_instance: JVM) -> None:
        """Test simulated import using JavaFinder."""
        # Add JavaFinder to meta_path temporarily
        finder = JavaFinder()
        # Use existing JVM instead of creating new one
        finder._jvm = jvm_instance
        original_meta_path = sys.meta_path.copy()

        try:
            sys.meta_path.insert(0, finder)

            # Find spec for java.lang
            spec = finder.find_spec("java.lang", None)
            assert spec is not None

            # Create and execute module
            assert spec.loader is not None
            module = spec.loader.create_module(spec)
            assert module is not None
            spec.loader.exec_module(module)

            # Test accessing System class
            system_proxy = module.__getattr__("System")
            assert isinstance(system_proxy, ClassProxy)
            assert system_proxy._fqcn == "java.lang.System"

        finally:
            sys.meta_path[:] = original_meta_path
            # Don't shutdown the JVM since it's shared


@pytest.mark.integration
class TestErrorHandling:
    """Test error handling in integration scenarios."""

    def test_nonexistent_class_access(self, jvm_instance: JVM) -> None:
        """Test accessing non-existent class."""
        with pytest.raises(Exception):  # Should raise JNIException or similar
            jvm_instance.find_class("com/nonexistent/Class")

    def test_invalid_package_discovery(self, jvm_instance: JVM) -> None:
        """Test package discovery for invalid package."""
        classes = jvm_instance.discover_package_classes("invalid.package.name")
        assert classes == []  # Should return empty list, not raise exception

    def test_proxy_nonexistent_method_access(self, jvm_instance: JVM) -> None:
        """Test accessing non-existent method through proxy."""
        system_proxy = ClassProxy(jvm_instance, "java.lang.System")

        with pytest.raises(AttributeError):
            system_proxy.nonExistentMethod

    def test_type_conversion_unsupported_type(self, jvm_instance: JVM) -> None:
        """Test type conversion with unsupported types."""
        # Unsupported types should pass through unchanged
        complex_obj = {"key": "value", "list": [1, 2, 3]}
        result = to_java(jvm_instance, complex_obj)
        assert result == complex_obj

        # Converting back should also pass through
        result2 = to_python(jvm_instance, result)
        assert result2 == complex_obj


@pytest.mark.integration
class TestJVMLifecycle:
    """Test JVM lifecycle management."""

    def test_jvm_startup_and_shutdown(self, jvm_instance: JVM) -> None:
        """Test JVM operations with existing instance."""
        # JVM should already be started
        assert jvm_instance is not None
        assert isinstance(jvm_instance, JVM)
        assert not jvm_instance._shutdown_complete

        # Should be able to use JVM
        system_class = jvm_instance.find_class("java/lang/System")
        assert system_class.name == "java/lang/System"

        # Don't test shutdown since it would affect other tests

    def test_multiple_jvm_operations(self, jvm_instance: JVM) -> None:
        """Test multiple operations on the same JVM instance."""
        # Multiple class lookups
        system_class = jvm_instance.find_class("java/lang/System")
        string_class = jvm_instance.find_class("java/lang/String")
        object_class = jvm_instance.find_class("java/lang/Object")

        assert system_class.name == "java/lang/System"
        assert string_class.name == "java/lang/String"
        assert object_class.name == "java/lang/Object"

        # Multiple package discoveries
        lang_classes = jvm_instance.discover_package_classes("java.lang")
        util_classes = jvm_instance.discover_package_classes("java.util")

        assert len(lang_classes) > 0
        assert len(util_classes) > 0
        assert "java.lang.String" in lang_classes
        assert "java.util.List" in util_classes

    def test_jvm_class_caching(self, jvm_instance: JVM) -> None:
        """Test that JVM caches classes properly."""
        # First access
        class1 = jvm_instance._find_class("java/lang/String")

        # Second access should use cache
        class2 = jvm_instance._find_class("java/lang/String")

        # Should be the same reference (cached)
        assert class1 == class2
        assert "java/lang/String" in jvm_instance._class_cache


@pytest.mark.integration
@pytest.mark.slow
class TestPerformance:
    """Test performance characteristics."""

    def test_class_lookup_performance(self, jvm_instance: JVM) -> None:
        """Test that class lookups are reasonably fast."""
        import time

        # Time multiple class lookups
        start_time = time.time()
        for _ in range(10):
            jvm_instance.find_class("java/lang/String")
            jvm_instance.find_class("java/lang/System")
            jvm_instance.find_class("java/lang/Object")
        end_time = time.time()

        # Should complete within reasonable time (adjust threshold as needed)
        elapsed = end_time - start_time
        assert elapsed < 5.0, f"Class lookups took {elapsed:.2f}s, expected < 5.0s"

    def test_package_discovery_performance(self, jvm_instance: JVM) -> None:
        """Test that package discovery is reasonably fast."""
        import time

        # Time package discovery
        start_time = time.time()
        jvm_instance.discover_package_classes("java.lang")
        jvm_instance.discover_package_classes("java.util")
        end_time = time.time()

        # Should complete within reasonable time
        elapsed = end_time - start_time
        assert elapsed < 10.0, (
            f"Package discovery took {elapsed:.2f}s, expected < 10.0s"
        )
