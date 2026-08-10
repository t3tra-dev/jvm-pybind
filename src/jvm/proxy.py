from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional, cast

from .jvm import JVM, JavaClass
from .signature import (
    array_component_type,
    is_array,
    java_type_to_descriptor,
    method_descriptor,
)
from .typeconv import to_python

if TYPE_CHECKING:
    from .classpath import ClasspathIndex


class PackageProxy:
    """Javaパッケージプロキシ"""

    def __init__(
        self,
        jvm: JVM,
        pkg_name: str,
        classpath_index: Optional[ClasspathIndex] = None,
    ):
        self._jvm = jvm
        self._pkg = pkg_name
        self._classpath_index = classpath_index

    def __getattr__(self, item: str) -> Any:
        fqcn = f"{self._pkg}.{item}"

        if self._classpath_index is not None:
            if self._classpath_index.contains_class(fqcn):
                return ClassProxy(self._jvm, fqcn)
            if self._classpath_index.contains_package(fqcn):
                return PackageProxy(self._jvm, fqcn, self._classpath_index)
            if self._classpath_index.contains_package(self._pkg):
                raise AttributeError(item)

        try:
            self._jvm.find_class(fqcn.replace(".", "/"))
            return ClassProxy(self._jvm, fqcn)
        except Exception:
            return PackageProxy(self._jvm, fqcn, self._classpath_index)

    def __repr__(self) -> str:
        return f"<Java package {self._pkg}>"


class ClassProxy:
    """Javaクラスプロキシ"""

    def __init__(self, jvm: JVM, fqcn: str):
        self._jvm = jvm
        self._fqcn = fqcn
        self._jclass = None
        self._class_info: JavaClass | None = None

    @property
    def _cls(self) -> Any:
        if self._jclass is None:
            self._jclass = self._jvm._find_class(self._fqcn.replace(".", "/"))
        return self._jclass

    @property
    def _info(self) -> JavaClass:
        if self._class_info is None:
            self._class_info = self._jvm.find_class(self._fqcn.replace(".", "/"))
        return self._class_info

    def __getattr__(self, item: str) -> Any:
        # 静的フィールド
        for f in self._info.fields:
            if f.name == item and f.is_static:
                try:
                    sig = f.descriptor or _java_type_to_sig(f.type)
                    field_id = f.field_id or self._jvm.jni.GetStaticFieldID(
                        self._cls, item, sig
                    )
                    if not field_id:
                        raise RuntimeError(f"Field ID not found for {item}")

                    field_val = self._jvm.jni.GetTypedStaticField(
                        self._cls, field_id, f.type
                    )
                    return _convert_typed_result(self._jvm, field_val, f.type)
                except Exception as e:
                    raise RuntimeError(f"Failed to access static field {item}: {e}")

        # 静的メソッド
        matches = [m for m in self._info.methods if m.name == item and m.is_static]
        if matches:
            return MethodProxy(self._jvm, self._cls, matches)

        raise AttributeError(item)

    def __call__(self, *args: Any) -> ObjectProxy:
        constructor = _select_overload(self._info.constructors, args)
        if constructor is None:
            available = ", ".join(_build_sig(item) for item in self._info.constructors)
            raise TypeError(
                f"No matching constructor for {self._fqcn}{args!r}; "
                f"available: {available or 'none'}"
            )

        method_id = constructor.method_id or self._jvm.jni.GetMethodID(
            self._cls, "<init>", _build_sig(constructor)
        )
        if not method_id:
            raise RuntimeError(f"Constructor resolution failed for {self._fqcn}")

        result = self._jvm.jni.NewTypedObject(
            self._cls,
            method_id,
            constructor.parameters,
            *args,
        )
        if not result:
            raise RuntimeError(f"Construction failed for {self._fqcn}")
        return ObjectProxy(self._jvm, result)

    def __repr__(self) -> str:
        return f"<Java class {self._fqcn}>"


class ObjectProxy:
    """Javaオブジェクトプロキシ"""

    def __init__(self, jvm: JVM, jobject: Any):
        self._jvm = jvm
        self._jobject = jobject
        self._class_info: Any = None

    @property
    def _info(self) -> Any:
        if self._class_info is None:
            try:
                obj_class = self._jvm.jni.GetObjectClass(self._jobject)
                if not obj_class:
                    self._class_info = type(
                        "EmptyJavaClass", (), {"methods": [], "fields": []}
                    )()
                    return self._class_info

                methods = self._jvm._extract_all_methods(obj_class)
                fields = self._jvm._extract_all_fields(obj_class)
                self._class_info = type(
                    "DynamicJavaClass", (), {"methods": methods, "fields": fields}
                )()

            except Exception:
                self._class_info = type(
                    "EmptyJavaClass", (), {"methods": [], "fields": []}
                )()

        return self._class_info

    def __getattr__(self, item: str) -> Any:
        for field in self._info.fields:
            if field.name == item and not field.is_static:
                obj_class = self._jvm.jni.GetObjectClass(self._jobject)
                signature = field.descriptor or _java_type_to_sig(field.type)
                field_id = field.field_id or self._jvm.jni.GetFieldID(
                    obj_class, item, signature
                )
                if not field_id:
                    raise RuntimeError(f"Field ID not found for {item}")
                value = self._jvm.jni.GetTypedField(self._jobject, field_id, field.type)
                return _convert_typed_result(self._jvm, value, field.type)

        matches = [m for m in self._info.methods if m.name == item and not m.is_static]
        if matches:
            return InstanceMethodProxy(self._jvm, self._jobject, matches)
        raise AttributeError(item)

    def __repr__(self) -> str:
        return "<Java object>"


class InstanceMethodProxy:
    """Javaインスタンスメソッドプロキシ"""

    def __init__(self, jvm: JVM, jobject: Any, overloads: list[Any]):
        self._jvm = jvm
        self._jobject = jobject
        self._overloads = overloads

    def __call__(self, *args: Any) -> Any:
        cand = None
        try:
            cand = _select_overload(self._overloads, args)
            if not cand:
                raise RuntimeError(
                    f"No matching method found for {len(args)} arguments"
                )

            sig = _build_sig(cand)

            obj_class = self._jvm.jni.GetObjectClass(self._jobject)
            mid = cand.method_id or self._jvm.jni.GetMethodID(obj_class, cand.name, sig)
            if not mid:
                raise RuntimeError(f"MethodID resolve failed for {cand.name}")

            result = self._jvm.jni.CallTypedMethod(
                self._jobject,
                mid,
                cand.return_type,
                cand.parameters,
                *args,
            )
            return _convert_typed_result(self._jvm, result, cand.return_type)
        except Exception as e:
            method_name = cand.name if cand else "unknown"
            raise RuntimeError(f"Failed to call method {method_name}: {e}")

    def __repr__(self) -> str:
        ol = ", ".join(f"{m.name}/{len(m.parameters)}" for m in self._overloads)
        return f"<Java instance method [{ol}]>"


class MethodProxy:
    """Java静的メソッドプロキシ"""

    def __init__(self, jvm: JVM, jclass: Any, overloads: list[Any]):
        self._jvm = jvm
        self._jclass = jclass
        self._overloads = overloads

    def __call__(self, *args: Any) -> Any:
        cand = _select_overload(self._overloads, args)
        if cand is None:
            available = ", ".join(_build_sig(item) for item in self._overloads)
            raise TypeError(
                f"No matching overload for arguments {args!r}; available: {available}"
            )
        sig = _build_sig(cand)
        mid = cand.method_id or self._jvm.jni.GetStaticMethodID(
            self._jclass, cand.name, sig
        )
        if not mid:
            raise RuntimeError("MethodID resolve failed")

        result = self._jvm.jni.CallTypedStaticMethod(
            self._jclass,
            mid,
            cand.return_type,
            cand.parameters,
            *args,
        )
        return _convert_typed_result(self._jvm, result, cand.return_type)

    def __repr__(self) -> str:
        ol = ", ".join(f"{m.name}/{len(m.parameters)}" for m in self._overloads)
        return f"<Java static method [{ol}]>"


def _java_type_to_sig(jtype: str) -> str:
    """Java型からJNIシグネチャ変換"""
    return java_type_to_descriptor(jtype)


def _build_sig(method: Any) -> str:
    """JNIシグネチャ構築"""
    if method.descriptor:
        return cast(str, method.descriptor)
    return method_descriptor(method.parameters, method.return_type)


def _argument_score(parameter_type: str, argument: Any) -> Optional[int]:
    if argument is None:
        return None if parameter_type in _PRIMITIVE_TYPES else 10
    if parameter_type == "boolean":
        return 0 if isinstance(argument, bool) else None
    if parameter_type in {"byte", "short", "int", "long"}:
        return _integral_argument_score(parameter_type, argument)
    if parameter_type in {"float", "double"}:
        return _floating_argument_score(parameter_type, argument)
    if parameter_type == "char":
        if not isinstance(argument, str) or len(argument) != 1:
            return None
        return 0 if ord(argument) <= 0xFFFF else None
    if parameter_type == "java.lang.String":
        return 0 if isinstance(argument, str) else None
    if parameter_type == "java.lang.Boolean":
        return 1 if isinstance(argument, bool) else None
    if parameter_type in _BOXED_INTEGRAL_TYPES:
        score = _integral_argument_score(
            _BOXED_INTEGRAL_TYPES[parameter_type], argument
        )
        return None if score is None else score + 1
    if parameter_type in {"java.lang.Float", "java.lang.Double"}:
        primitive_type = parameter_type.removeprefix("java.lang.").lower()
        score = _floating_argument_score(primitive_type, argument)
        return None if score is None else score + 1
    if parameter_type == "java.lang.Character":
        score = _argument_score("char", argument)
        return None if score is None else score + 1
    if is_array(parameter_type):
        return _array_argument_score(parameter_type, argument)
    if hasattr(argument, "_jobject"):
        return 0
    if isinstance(argument, str):
        return 5
    return 10


def _integral_argument_score(parameter_type: str, argument: Any) -> Optional[int]:
    if isinstance(argument, bool) or not isinstance(argument, int):
        return None
    lower, upper = _INTEGRAL_RANGES[parameter_type]
    if not lower <= argument <= upper:
        return None
    return {"int": 0, "long": 1, "short": 2, "byte": 3}[parameter_type]


def _floating_argument_score(parameter_type: str, argument: Any) -> Optional[int]:
    if isinstance(argument, bool) or not isinstance(argument, (int, float)):
        return None
    if isinstance(argument, int):
        return 4 if parameter_type == "double" else 5
    return 0 if parameter_type == "double" else 1


def _array_argument_score(parameter_type: str, argument: Any) -> Optional[int]:
    if not isinstance(argument, (list, tuple)):
        return None
    component_type = array_component_type(parameter_type)
    element_scores = [_argument_score(component_type, element) for element in argument]
    if not all(score is not None for score in element_scores):
        return None
    return sum(score for score in element_scores if score is not None)


def _select_overload(overloads: list[Any], args: tuple[Any, ...]) -> Optional[Any]:
    candidates: list[tuple[int, int, Any]] = []
    for position, overload in enumerate(overloads):
        if len(overload.parameters) != len(args):
            continue
        scores = [
            _argument_score(parameter, argument)
            for parameter, argument in zip(overload.parameters, args)
        ]
        if all(score is not None for score in scores):
            candidates.append(
                (
                    sum(score for score in scores if score is not None),
                    position,
                    overload,
                )
            )

    if not candidates:
        return None
    candidates.sort(key=lambda item: (item[0], item[1]))
    return candidates[0][2]


def _convert_typed_result(jvm: JVM, result: Any, return_type: str) -> Any:
    if return_type == "void":
        return None
    if return_type == "char":
        return chr(result)
    if return_type in _PRIMITIVE_TYPES:
        return result
    if is_array(return_type):
        component_type = array_component_type(return_type)
        values = jvm.jni.GetTypedArrayElements(result, return_type)
        return [_convert_typed_result(jvm, value, component_type) for value in values]
    return to_python(jvm, result)


_PRIMITIVE_TYPES = {
    "boolean",
    "byte",
    "char",
    "short",
    "int",
    "long",
    "float",
    "double",
}

_INTEGRAL_RANGES = {
    "byte": (-(2**7), 2**7 - 1),
    "short": (-(2**15), 2**15 - 1),
    "int": (-(2**31), 2**31 - 1),
    "long": (-(2**63), 2**63 - 1),
}

_BOXED_INTEGRAL_TYPES = {
    "java.lang.Byte": "byte",
    "java.lang.Short": "short",
    "java.lang.Integer": "int",
    "java.lang.Long": "long",
}
