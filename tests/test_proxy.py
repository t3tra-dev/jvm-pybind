"""Tests for proxy system functionality."""

from unittest.mock import Mock, patch

import pytest

from jvm.jvm import JavaClass, JavaField, JavaMethod
from jvm.proxy import (
    ClassProxy,
    InstanceMethodProxy,
    MethodProxy,
    ObjectProxy,
    PackageProxy,
    _argument_score,
    _build_sig,
    _java_type_to_sig,
)


class TestHelperFunctions:
    """Test helper functions for proxy system."""

    def test_java_type_to_sig_primitives(self) -> None:
        """Test Java primitive type to JNI signature conversion."""
        assert _java_type_to_sig("int") == "I"
        assert _java_type_to_sig("long") == "J"
        assert _java_type_to_sig("float") == "F"
        assert _java_type_to_sig("double") == "D"
        assert _java_type_to_sig("boolean") == "Z"
        assert _java_type_to_sig("void") == "V"
        assert _java_type_to_sig("byte") == "B"
        assert _java_type_to_sig("char") == "C"
        assert _java_type_to_sig("short") == "S"

    def test_java_type_to_sig_objects(self) -> None:
        """Test Java object type to JNI signature conversion."""
        assert _java_type_to_sig("java.lang.String") == "Ljava/lang/String;"
        assert _java_type_to_sig("java.lang.Object") == "Ljava/lang/Object;"
        assert _java_type_to_sig("java.util.List") == "Ljava/util/List;"
        assert _java_type_to_sig("com.example.MyClass") == "Lcom/example/MyClass;"

    def test_java_type_to_sig_arrays(self) -> None:
        assert _java_type_to_sig("int[]") == "[I"
        assert _java_type_to_sig("java.lang.String[]") == "[Ljava/lang/String;"
        assert _java_type_to_sig("[[Ljava.lang.String;") == "[[Ljava/lang/String;"

    def test_build_sig_no_params_void_return(self) -> None:
        """Test building signature for method with no params and void return."""
        method = JavaMethod(
            name="doSomething", parameters=[], return_type="void", is_static=True
        )

        result = _build_sig(method)

        assert result == "()V"

    def test_build_sig_with_params_object_return(self) -> None:
        """Test building signature for method with params and object return."""
        method = JavaMethod(
            name="getValue",
            parameters=["java.lang.String", "int"],
            return_type="java.lang.Object",
            is_static=False,
        )

        result = _build_sig(method)

        assert result == "(Ljava/lang/String;I)Ljava/lang/Object;"

    def test_build_sig_complex_method(self) -> None:
        """Test building signature for complex method."""
        method = JavaMethod(
            name="complexMethod",
            parameters=["java.lang.String", "boolean", "java.util.List"],
            return_type="java.lang.String",
            is_static=True,
        )

        result = _build_sig(method)

        assert result == "(Ljava/lang/String;ZLjava/util/List;)Ljava/lang/String;"

    @pytest.mark.parametrize(
        ("java_type", "value", "matches"),
        [
            ("byte", 127, True),
            ("byte", 128, False),
            ("short", -(2**15), True),
            ("short", -(2**15) - 1, False),
            ("int", 2**31 - 1, True),
            ("int", 2**31, False),
            ("long", -(2**63), True),
            ("long", -(2**63) - 1, False),
        ],
    )
    def test_integral_argument_ranges(
        self, java_type: str, value: int, matches: bool
    ) -> None:
        assert (_argument_score(java_type, value) is not None) is matches

    def test_boxed_integral_overloads_are_scored_by_target_type(self) -> None:
        assert _argument_score("java.lang.Integer", 42) == 1
        assert _argument_score("java.lang.Long", 42) == 2
        assert _argument_score("java.lang.Integer", 2**31) is None

    def test_java_char_rejects_supplementary_code_point(self) -> None:
        assert _argument_score("char", "A") == 0
        assert _argument_score("char", "U0001f600") is None


class TestPackageProxy:
    """Test PackageProxy functionality."""

    def test_package_proxy_initialization(self, mock_jvm: Mock) -> None:
        """Test PackageProxy initialization."""
        pkg_name = "java.lang"
        proxy = PackageProxy(mock_jvm, pkg_name)

        assert proxy._jvm == mock_jvm
        assert proxy._pkg == pkg_name

    def test_package_proxy_getattr_class_exists(self, mock_jvm: Mock) -> None:
        """Test getting attribute when class exists."""
        pkg_name = "java.lang"
        proxy = PackageProxy(mock_jvm, pkg_name)

        # Mock successful class finding
        mock_jvm.find_class.return_value = Mock()

        result = proxy.System

        assert isinstance(result, ClassProxy)
        assert result._fqcn == "java.lang.System"
        mock_jvm.find_class.assert_called_with("java/lang/System")

    def test_package_proxy_getattr_class_not_exists(self, mock_jvm: Mock) -> None:
        """Test getting attribute when class doesn't exist (returns sub-package)."""
        pkg_name = "java"
        proxy = PackageProxy(mock_jvm, pkg_name)

        # Mock failed class finding
        mock_jvm.find_class.side_effect = Exception("Class not found")

        result = proxy.util

        assert isinstance(result, PackageProxy)
        assert result._pkg == "java.util"

    def test_package_proxy_repr(self, mock_jvm: Mock) -> None:
        """Test PackageProxy string representation."""
        pkg_name = "java.lang"
        proxy = PackageProxy(mock_jvm, pkg_name)

        result = repr(proxy)

        assert result == "<Java package java.lang>"


class TestClassProxy:
    """Test ClassProxy functionality."""

    def test_class_proxy_initialization(self, mock_jvm: Mock) -> None:
        """Test ClassProxy initialization."""
        fqcn = "java.lang.System"
        proxy = ClassProxy(mock_jvm, fqcn)

        assert proxy._jvm == mock_jvm
        assert proxy._fqcn == fqcn
        assert proxy._jclass is None
        assert proxy._class_info is None

    def test_class_proxy_cls_property_lazy_loading(self, mock_jvm: Mock) -> None:
        """Test lazy loading of class reference."""
        fqcn = "java.lang.System"
        proxy = ClassProxy(mock_jvm, fqcn)
        mock_class_ref = 0x12345678

        mock_jvm._find_class.return_value = mock_class_ref

        # First access should trigger loading
        result = proxy._cls

        assert result == mock_class_ref
        assert proxy._jclass == mock_class_ref
        mock_jvm._find_class.assert_called_once_with("java/lang/System")

        # Second access should use cached value
        result2 = proxy._cls
        assert result2 == mock_class_ref
        # Should not call _find_class again
        assert mock_jvm._find_class.call_count == 1

    def test_class_proxy_info_property_lazy_loading(
        self, mock_jvm: Mock, sample_java_class: JavaClass
    ) -> None:
        """Test lazy loading of class info."""
        fqcn = "java.lang.System"
        proxy = ClassProxy(mock_jvm, fqcn)

        mock_jvm.find_class.return_value = sample_java_class

        # First access should trigger loading
        result = proxy._info

        assert result == sample_java_class
        assert proxy._class_info == sample_java_class
        mock_jvm.find_class.assert_called_once_with("java/lang/System")

        # Second access should use cached value
        result2 = proxy._info
        assert result2 == sample_java_class
        # Should not call find_class again
        assert mock_jvm.find_class.call_count == 1

    def test_class_proxy_getattr_static_field(self, mock_jvm: Mock) -> None:
        """Test accessing static field."""
        fqcn = "java.lang.System"
        proxy = ClassProxy(mock_jvm, fqcn)

        # Create mock class info with static field
        fields = [JavaField(name="out", type="java.io.PrintStream", is_static=True)]
        methods: list[JavaMethod] = []
        class_info = JavaClass(name=fqcn, methods=methods, fields=fields)

        mock_class_ref = 0x12345678
        mock_field_value = 0x87654321

        mock_jvm._find_class.return_value = mock_class_ref
        mock_jvm.find_class.return_value = class_info
        mock_jvm.jni.GetStaticFieldID.return_value = 0x11111111
        mock_jvm.jni.GetTypedStaticField.return_value = mock_field_value

        with patch("jvm.proxy.to_python") as mock_to_python:
            mock_to_python.return_value = "mocked_python_value"

            result = proxy.out

            assert result == "mocked_python_value"
            mock_jvm.jni.GetStaticFieldID.assert_called_once()
            mock_jvm.jni.GetTypedStaticField.assert_called_once_with(
                mock_class_ref, 0x11111111, "java.io.PrintStream"
            )

    def test_class_proxy_getattr_static_method(self, mock_jvm: Mock) -> None:
        """Test accessing static method."""
        fqcn = "java.lang.System"
        proxy = ClassProxy(mock_jvm, fqcn)

        # Create mock class info with static method
        methods = [
            JavaMethod(
                name="getProperty",
                parameters=["java.lang.String"],
                return_type="java.lang.String",
                is_static=True,
            )
        ]
        fields: list[JavaField] = []
        class_info = JavaClass(name=fqcn, methods=methods, fields=fields)

        mock_class_ref = 0x12345678

        mock_jvm._find_class.return_value = mock_class_ref
        mock_jvm.find_class.return_value = class_info

        result = proxy.getProperty

        assert isinstance(result, MethodProxy)
        assert result._jclass == mock_class_ref
        assert len(result._overloads) == 1
        assert result._overloads[0].name == "getProperty"

    def test_class_proxy_getattr_not_found(self, mock_jvm: Mock) -> None:
        """Test accessing non-existent attribute."""
        fqcn = "java.lang.System"
        proxy = ClassProxy(mock_jvm, fqcn)

        # Create empty class info
        class_info = JavaClass(name=fqcn, methods=[], fields=[])

        mock_jvm.find_class.return_value = class_info

        with pytest.raises(AttributeError, match="nonExistentAttribute"):
            proxy.nonExistentAttribute

    def test_class_proxy_repr(self, mock_jvm: Mock) -> None:
        """Test ClassProxy string representation."""
        fqcn = "java.lang.System"
        proxy = ClassProxy(mock_jvm, fqcn)

        result = repr(proxy)

        assert result == "<Java class java.lang.System>"


class TestObjectProxy:
    """Test ObjectProxy functionality."""

    def test_object_proxy_initialization(self, mock_jvm: Mock) -> None:
        """Test ObjectProxy initialization."""
        jobject = 0x12345678
        proxy = ObjectProxy(mock_jvm, jobject)

        assert proxy._jvm == mock_jvm
        assert proxy._jobject == jobject
        assert proxy._class_info is None

    def test_object_proxy_info_property_success(self, mock_jvm: Mock) -> None:
        """Test successful class info retrieval."""
        jobject = 0x12345678
        proxy = ObjectProxy(mock_jvm, jobject)

        mock_obj_class = 0x87654321
        mock_methods = [
            JavaMethod(
                name="toString",
                parameters=[],
                return_type="java.lang.String",
                is_static=False,
            )
        ]
        mock_fields = [
            JavaField(name="value", type="java.lang.String", is_static=False)
        ]

        mock_jvm.jni.GetObjectClass.return_value = mock_obj_class
        mock_jvm._extract_all_methods.return_value = mock_methods
        mock_jvm._extract_all_fields.return_value = mock_fields

        result = proxy._info

        assert result.methods == mock_methods
        assert result.fields == mock_fields
        mock_jvm.jni.GetObjectClass.assert_called_once_with(jobject)

    def test_object_proxy_info_property_get_class_failure(self, mock_jvm: Mock) -> None:
        """Test class info retrieval when GetObjectClass fails."""
        jobject = 0x12345678
        proxy = ObjectProxy(mock_jvm, jobject)

        mock_jvm.jni.GetObjectClass.return_value = None

        result = proxy._info

        assert result.methods == []
        assert result.fields == []

    def test_object_proxy_info_property_exception(self, mock_jvm: Mock) -> None:
        """Test class info retrieval with exception."""
        jobject = 0x12345678
        proxy = ObjectProxy(mock_jvm, jobject)

        mock_jvm.jni.GetObjectClass.side_effect = Exception("Test error")

        result = proxy._info

        assert result.methods == []
        assert result.fields == []

    def test_object_proxy_getattr_method_found(self, mock_jvm: Mock) -> None:
        """Test accessing instance method."""
        jobject = 0x12345678
        proxy = ObjectProxy(mock_jvm, jobject)

        mock_methods = [
            JavaMethod(
                name="toString",
                parameters=[],
                return_type="java.lang.String",
                is_static=False,
            ),
            JavaMethod(
                name="toString",
                parameters=["java.lang.String"],
                return_type="java.lang.String",
                is_static=False,
            ),  # Overload
        ]

        # Mock the _info property
        proxy._class_info = type(
            "MockClass", (), {"methods": mock_methods, "fields": []}
        )()

        result = proxy.toString

        assert isinstance(result, InstanceMethodProxy)
        assert result._jobject == jobject
        assert len(result._overloads) == 2

    def test_object_proxy_getattr_method_not_found(self, mock_jvm: Mock) -> None:
        """Test accessing non-existent method."""
        jobject = 0x12345678
        proxy = ObjectProxy(mock_jvm, jobject)

        # Mock empty class info
        proxy._class_info = type("MockClass", (), {"methods": [], "fields": []})()

        with pytest.raises(AttributeError, match="nonExistentMethod"):
            proxy.nonExistentMethod

    def test_object_proxy_repr(self, mock_jvm: Mock) -> None:
        """Test ObjectProxy string representation."""
        jobject = 0x12345678
        proxy = ObjectProxy(mock_jvm, jobject)

        result = repr(proxy)

        assert result == "<Java object>"


class TestMethodProxy:
    """Test MethodProxy functionality."""

    def test_method_proxy_initialization(self, mock_jvm: Mock) -> None:
        """Test MethodProxy initialization."""
        jclass = 0x12345678
        overloads = [
            JavaMethod(
                name="valueOf",
                parameters=["int"],
                return_type="java.lang.String",
                is_static=True,
            ),
            JavaMethod(
                name="valueOf",
                parameters=["boolean"],
                return_type="java.lang.String",
                is_static=True,
            ),
        ]

        proxy = MethodProxy(mock_jvm, jclass, overloads)

        assert proxy._jvm == mock_jvm
        assert proxy._jclass == jclass
        assert proxy._overloads == overloads

    def test_method_proxy_call_success(self, mock_jvm: Mock) -> None:
        """Test successful method call."""
        jclass = 0x12345678
        overloads = [
            JavaMethod(
                name="valueOf",
                parameters=["int"],
                return_type="java.lang.String",
                is_static=True,
            )
        ]

        proxy = MethodProxy(mock_jvm, jclass, overloads)

        mock_method_id = 0x87654321
        mock_result = 0x11111111

        mock_jvm.jni.GetStaticMethodID.return_value = mock_method_id
        mock_jvm.jni.CallTypedStaticMethod.return_value = mock_result

        with patch("jvm.proxy.to_python") as mock_to_python:
            mock_to_python.return_value = "42"

            result = proxy(42)

            assert result == "42"
            mock_to_python.assert_called_once_with(mock_jvm, mock_result)
            mock_jvm.jni.GetStaticMethodID.assert_called_once_with(
                jclass, "valueOf", "(I)Ljava/lang/String;"
            )
            mock_jvm.jni.CallTypedStaticMethod.assert_called_once_with(
                jclass,
                mock_method_id,
                "java.lang.String",
                ["int"],
                42,
            )

    def test_method_proxy_call_no_matching_overload(self, mock_jvm: Mock) -> None:
        """Test method call with no matching overload."""
        jclass = 0x12345678
        overloads = [
            JavaMethod(
                name="valueOf",
                parameters=["int"],
                return_type="java.lang.String",
                is_static=True,
            )
        ]

        proxy = MethodProxy(mock_jvm, jclass, overloads)

        with pytest.raises(TypeError, match="No matching overload"):
            proxy("string_arg")

    def test_method_proxy_call_method_id_failure(self, mock_jvm: Mock) -> None:
        """Test method call when method ID resolution fails."""
        jclass = 0x12345678
        overloads = [
            JavaMethod(
                name="valueOf",
                parameters=["int"],
                return_type="java.lang.String",
                is_static=True,
            )
        ]

        proxy = MethodProxy(mock_jvm, jclass, overloads)

        mock_jvm.jni.GetStaticMethodID.return_value = None  # Failure

        with pytest.raises(RuntimeError, match="MethodID resolve failed"):
            proxy(42)

    def test_method_proxy_repr(self, mock_jvm: Mock) -> None:
        """Test MethodProxy string representation."""
        jclass = 0x12345678
        overloads = [
            JavaMethod(
                name="valueOf",
                parameters=["int"],
                return_type="java.lang.String",
                is_static=True,
            ),
            JavaMethod(
                name="valueOf",
                parameters=["boolean"],
                return_type="java.lang.String",
                is_static=True,
            ),
        ]

        proxy = MethodProxy(mock_jvm, jclass, overloads)

        result = repr(proxy)

        assert "valueOf/1" in result
        assert "Java static method" in result


class TestInstanceMethodProxy:
    """Test InstanceMethodProxy functionality."""

    def test_instance_method_proxy_initialization(self, mock_jvm: Mock) -> None:
        """Test InstanceMethodProxy initialization."""
        jobject = 0x12345678
        overloads = [
            JavaMethod(
                name="toString",
                parameters=[],
                return_type="java.lang.String",
                is_static=False,
            )
        ]

        proxy = InstanceMethodProxy(mock_jvm, jobject, overloads)

        assert proxy._jvm == mock_jvm
        assert proxy._jobject == jobject
        assert proxy._overloads == overloads

    def test_instance_method_proxy_call_void_method(self, mock_jvm: Mock) -> None:
        """Test calling void instance method."""
        jobject = 0x12345678
        overloads = [
            JavaMethod(
                name="doSomething", parameters=[], return_type="void", is_static=False
            )
        ]

        proxy = InstanceMethodProxy(mock_jvm, jobject, overloads)

        mock_obj_class = 0x87654321
        mock_method_id = 0x11111111

        mock_jvm.jni.GetObjectClass.return_value = mock_obj_class
        mock_jvm.jni.GetMethodID.return_value = mock_method_id

        mock_jvm.jni.CallTypedMethod.return_value = None

        result = proxy()

        assert result is None
        mock_jvm.jni.CallTypedMethod.assert_called_once_with(
            jobject, mock_method_id, "void", []
        )

    def test_instance_method_proxy_call_object_method(self, mock_jvm: Mock) -> None:
        """Test calling object-returning instance method."""
        jobject = 0x12345678
        overloads = [
            JavaMethod(
                name="toString",
                parameters=[],
                return_type="java.lang.String",
                is_static=False,
            )
        ]

        proxy = InstanceMethodProxy(mock_jvm, jobject, overloads)

        mock_obj_class = 0x87654321
        mock_method_id = 0x11111111
        mock_result = 0x22222222

        mock_jvm.jni.GetObjectClass.return_value = mock_obj_class
        mock_jvm.jni.GetMethodID.return_value = mock_method_id
        mock_jvm.jni.CallTypedMethod.return_value = mock_result

        with patch("jvm.proxy.to_python") as mock_to_python:
            mock_to_python.return_value = "string_result"

            result = proxy()

            assert result == "string_result"
            mock_jvm.jni.CallTypedMethod.assert_called_once_with(
                jobject,
                mock_method_id,
                "java.lang.String",
                [],
            )

    def test_instance_method_proxy_call_with_args(self, mock_jvm: Mock) -> None:
        """Test calling instance method with arguments."""
        jobject = 0x12345678
        overloads = [
            JavaMethod(
                name="setValue",
                parameters=["java.lang.String"],
                return_type="void",
                is_static=False,
            )
        ]

        proxy = InstanceMethodProxy(mock_jvm, jobject, overloads)

        mock_obj_class = 0x87654321
        mock_method_id = 0x11111111

        mock_jvm.jni.GetObjectClass.return_value = mock_obj_class
        mock_jvm.jni.GetMethodID.return_value = mock_method_id

        mock_jvm.jni.CallTypedMethod.return_value = None

        result = proxy("test_value")

        assert result is None
        mock_jvm.jni.CallTypedMethod.assert_called_once_with(
            jobject,
            mock_method_id,
            "void",
            ["java.lang.String"],
            "test_value",
        )

    def test_instance_method_proxy_call_no_matching_overload(
        self, mock_jvm: Mock
    ) -> None:
        """Test instance method call with no matching overload."""
        jobject = 0x12345678
        overloads = [
            JavaMethod(
                name="setValue",
                parameters=["java.lang.String"],
                return_type="void",
                is_static=False,
            )
        ]

        proxy = InstanceMethodProxy(mock_jvm, jobject, overloads)

        with pytest.raises(
            RuntimeError, match="No matching method found for 0 arguments"
        ):
            proxy()  # Method expects 1 argument, we provide 0

    def test_instance_method_proxy_call_exception(self, mock_jvm: Mock) -> None:
        """Test instance method call with exception."""
        jobject = 0x12345678
        overloads = [
            JavaMethod(
                name="toString",
                parameters=[],
                return_type="java.lang.String",
                is_static=False,
            )
        ]

        proxy = InstanceMethodProxy(mock_jvm, jobject, overloads)

        mock_jvm.jni.GetObjectClass.side_effect = Exception("Test error")

        with pytest.raises(RuntimeError, match="Failed to call method toString"):
            proxy()

    def test_instance_method_proxy_repr(self, mock_jvm: Mock) -> None:
        """Test InstanceMethodProxy string representation."""
        jobject = 0x12345678
        overloads = [
            JavaMethod(
                name="toString",
                parameters=[],
                return_type="java.lang.String",
                is_static=False,
            ),
            JavaMethod(
                name="toString",
                parameters=["java.lang.String"],
                return_type="java.lang.String",
                is_static=False,
            ),
        ]

        proxy = InstanceMethodProxy(mock_jvm, jobject, overloads)

        result = repr(proxy)

        assert "toString/0" in result
        assert "toString/1" in result
        assert "Java instance method" in result
