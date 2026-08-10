from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .jni import JNIHelper
from .logger import logger
from .signature import java_type_to_descriptor, method_descriptor

# 定数
STATIC_MODIFIER = 8
MAX_PARAM_COUNT = 50


class JNIException(Exception):
    """JNI例外"""

    pass


@dataclass
class JavaMethod:
    """Javaメソッド情報"""

    name: str
    parameters: List[str]
    return_type: str
    is_static: bool = False
    descriptor: Optional[str] = None
    method_id: Optional[Any] = None

    def __repr__(self) -> str:
        params_str = ", ".join(self.parameters) if self.parameters else ""
        static_str = " (static)" if self.is_static else ""
        return f"JavaMethod(name='{self.name}', params=[{params_str}], returns='{self.return_type}'{static_str})"


@dataclass
class JavaField:
    """Javaフィールド情報"""

    name: str
    type: str
    is_static: bool = False
    descriptor: Optional[str] = None
    field_id: Optional[Any] = None

    def __repr__(self) -> str:
        static_str = " (static)" if self.is_static else ""
        return f"JavaField(name='{self.name}', type='{self.type}'{static_str})"


@dataclass
class JavaClass:
    """Javaクラス情報"""

    name: str
    methods: List[JavaMethod]
    fields: List[JavaField]
    constructors: List[JavaMethod] = field(default_factory=list)

    def __repr__(self) -> str:
        methods_str = f", {len(self.methods)} methods" if self.methods else ""
        fields_str = f", {len(self.fields)} fields" if self.fields else ""
        return f"JavaClass(name='{self.name}'{methods_str}{fields_str})"


class JVM:
    """JVM接続とリソース管理"""

    def __init__(
        self,
        jvm_ptr: Any,
        env_ptr: Any,
        classpath: Optional[List[str]] = None,
    ) -> None:
        self.jvm: Any = jvm_ptr
        self.env: Any = env_ptr
        self.jni: JNIHelper = JNIHelper(env_ptr)
        self._shutdown_complete: bool = False
        self._class_cache: Dict[str, Any] = {}
        self.classpath = classpath or []

    def graceful_shutdown(self) -> None:
        """安全なJVMシャットダウン"""
        if self._shutdown_complete:
            return

        try:
            logger.debug("Initiating graceful JVM shutdown...")

            # クラス参照をクリーンアップ
            logger.debug(
                f"Cleaning up {len(self._class_cache)} cached class references"
            )
            for class_name, global_ref in self._class_cache.items():
                try:
                    if global_ref:
                        self.jni.DeleteGlobalRef(global_ref)
                        logger.debug(
                            f"Cleaned up global reference for class: {class_name}"
                        )
                except Exception as e:
                    logger.warning(
                        f"Failed to cleanup global reference for {class_name}: {e}"
                    )

            self._class_cache.clear()

            if self.jni.PushLocalFrame(64) == 0:
                try:
                    runtime_class = self.jni.FindClass("java/lang/Runtime")
                    if runtime_class:
                        get_runtime_method = self.jni.GetStaticMethodID(
                            runtime_class, "getRuntime", "()Ljava/lang/Runtime;"
                        )
                        if get_runtime_method:
                            runtime_instance = self.jni.CallStaticObjectMethod(
                                runtime_class, get_runtime_method
                            )
                            if runtime_instance:
                                halt_method = self.jni.GetMethodID(
                                    runtime_class, "halt", "(I)V"
                                )
                                if halt_method:
                                    logger.debug(
                                        "Calling Runtime.halt(0) to immediately terminate JVM"
                                    )
                                    self.jni.CallVoidMethod(
                                        runtime_instance, halt_method, 0
                                    )
                finally:
                    self.jni.PopLocalFrame(None)

            self._shutdown_complete = True
            logger.debug("JVM graceful shutdown completed")

        except Exception as e:
            logger.warning(f"Error during graceful shutdown: {e}")
            self._shutdown_complete = True

    def _find_class(self, class_name: str) -> Any:
        """クラス検索（キャッシュ付き）"""
        if class_name in self._class_cache:
            logger.debug(f"Found cached class: {class_name}")
            return self._class_cache[class_name]

        try:
            jclass = self.jni.FindClass(class_name)
            if not jclass:
                raise JNIException(f"Could not find class: {class_name}")

            global_ref = self.jni.NewGlobalRef(jclass)
            if global_ref:
                self._class_cache[class_name] = global_ref
                logger.debug(f"Cached class as global reference: {class_name}")
                return global_ref
            else:
                logger.warning(
                    f"Failed to create global reference for {class_name}, using local reference"
                )
                return jclass

        except Exception as e:
            raise JNIException(f"Failed to find class {class_name}: {e}")

    def _get_method_id(self, jclass: Any, method_name: str, signature: str) -> Any:
        """メソッドID取得"""
        try:
            method_id = self.jni.GetMethodID(jclass, method_name, signature)
            if not method_id:
                raise JNIException(
                    f"Could not find method: {method_name} with signature: {signature}"
                )
            return method_id
        except Exception as e:
            raise JNIException(f"Failed to get method ID for {method_name}: {e}")

    def _call_object_method(self, obj: Any, method_id: Any) -> Any:
        """オブジェクトメソッド呼び出し"""
        if not obj or not method_id:
            raise JNIException("Object or method ID is null")

        try:
            return self.jni.CallObjectMethod(obj, method_id)
        except Exception as e:
            raise JNIException(f"Failed to call object method: {e}")

    def _get_array_length(self, array: Any) -> int:
        """配列長取得"""
        if not array:
            raise JNIException("Array is null")

        try:
            return self.jni.GetArrayLength(array)
        except Exception as e:
            raise JNIException(f"Failed to get array length: {e}")

    def _get_object_array_element(self, array: Any, index: int) -> Any:
        """配列要素取得"""
        if not array:
            raise JNIException("Array is null")

        try:
            return self.jni.GetObjectArrayElement(array, index)
        except Exception as e:
            raise JNIException(
                f"Failed to get object array element at index {index}: {e}"
            )

    def _get_string_length(self, jstring: Any) -> int:
        """JNI GetStringLength function wrapper"""
        if not jstring:
            return 0

        try:
            return self.jni.GetStringLength(jstring)
        except Exception as e:
            raise JNIException(f"Failed to get string length: {e}")

    def _get_string_utf_length(self, jstring: Any) -> int:
        """JNI GetStringUTFLength function wrapper"""
        if not jstring:
            return 0

        try:
            return self.jni.GetStringUTFLength(jstring)
        except Exception as e:
            raise JNIException(f"Failed to get string UTF length: {e}")

    def _get_string_utf_chars(self, jstring: Any) -> str:
        """JNI GetStringUTFChars function wrapper"""
        if not jstring:
            return ""

        try:
            result = self.jni.GetStringUTFChars(jstring)
            return result if result is not None else ""
        except Exception:
            return "get_error"

    def _get_object_class(self, obj: Any) -> Any:
        """JNI GetObjectClass function wrapper"""
        if not obj:
            raise JNIException("Object is null")

        try:
            return self.jni.GetObjectClass(obj)
        except Exception as e:
            raise JNIException(f"Failed to get object class: {e}")

    def _get_class_name_from_jclass(self, jclass: Any) -> str:
        """jclass (クラス参照) からクラス名を取得"""
        # クラス名取得を無効化 JNI仕様違反を避ける
        # jclassは単純なクラス参照
        _ = jclass
        return "JavaClass"

    def _call_object_method_with_signature_direct(
        self, obj: Any, method_name: str, signature: str
    ) -> Any:
        """オブジェクトのメソッドを直接呼び出す"""
        obj_class = self.jni.GetObjectClass(obj)
        if not obj_class:
            raise JNIException("Failed to get object class")

        method_id = self.jni.GetMethodID(obj_class, method_name, signature)
        if not method_id:
            raise JNIException(f"Could not find method: {method_name}")

        return self.jni.CallObjectMethod(obj, method_id)

    def _extract_method_name(self, method_obj: Any) -> str:
        """Methodオブジェクトからメソッド名を取得"""
        try:
            name_string = self._call_object_method_with_signature_direct(
                method_obj, "getName", "()Ljava/lang/String;"
            )
            return (
                self._get_string_utf_chars(name_string)
                if name_string
                else "unknown_method"
            )
        except Exception:
            return "unknown_method"

    def _extract_method_return_type(self, method_obj: Any) -> str:
        """Methodオブジェクトから戻り値型を取得"""
        try:
            return_type_obj = self._call_object_method_with_signature_direct(
                method_obj, "getReturnType", "()Ljava/lang/Class;"
            )
            if return_type_obj:
                return_type_string = self._call_object_method_with_signature_direct(
                    return_type_obj, "getName", "()Ljava/lang/String;"
                )
                if return_type_string:
                    return_type = self._get_string_utf_chars(return_type_string)
                    # 安全性チェック: 空文字列の場合はデフォルト値
                    if not return_type or return_type.strip() == "":
                        return "void"
                    return return_type
        except Exception:
            pass
        return "void"

    def _extract_method_parameters(self, method_obj: Any) -> List[str]:
        """Methodオブジェクトからパラメータ型リストを取得"""
        try:
            param_types_array = self._call_object_method_with_signature_direct(
                method_obj, "getParameterTypes", "()[Ljava/lang/Class;"
            )
            if not param_types_array:
                return []

            param_count = self._get_array_length(param_types_array)
            # 配列が大きすぎる場合は処理を制限 (安全性優先)
            if param_count > MAX_PARAM_COUNT:
                return ["..."]

            parameters = []
            for i in range(param_count):
                try:
                    param_class = self._get_object_array_element(param_types_array, i)
                    if param_class:
                        param_name_string = (
                            self._call_object_method_with_signature_direct(
                                param_class, "getName", "()Ljava/lang/String;"
                            )
                        )
                        if param_name_string:
                            param_name = self._get_string_utf_chars(param_name_string)
                            # 安全性チェック: 空文字列の場合はデフォルト値
                            if param_name and param_name.strip():
                                parameters.append(param_name)
                            else:
                                parameters.append("Object")
                        else:
                            parameters.append("Object")
                    else:
                        parameters.append("Object")
                except Exception:
                    # 個別のパラメータ取得に失敗した場合は Object
                    parameters.append("Object")
            return parameters
        except Exception:
            return []

    def _extract_method_is_static(self, method_obj: Any) -> bool:
        """Methodオブジェクトから静的メソッドかを判定"""
        try:
            obj_class = self.jni.GetObjectClass(method_obj)
            if not obj_class:
                return False
            method_id = self.jni.GetMethodID(obj_class, "getModifiers", "()I")
            if not method_id:
                return False
            modifiers = self.jni.CallIntMethod(method_obj, method_id)
            if modifiers is not None:
                # Modifier.STATICのビット演算で確認
                return bool(modifiers & STATIC_MODIFIER)
        except Exception:
            pass
        return False

    def _extract_method_info(self, method_obj: Any) -> JavaMethod:
        """`java.lang.reflect.Method` オブジェクトから情報を抽出"""
        try:
            name = self._extract_method_name(method_obj)

            return_type = self._extract_method_return_type(method_obj)

            parameters = self._extract_method_parameters(method_obj)

            is_static = self._extract_method_is_static(method_obj)

            descriptor = method_descriptor(parameters, return_type)
            method_id = self.jni.FromReflectedMethod(method_obj)

            return JavaMethod(
                name=name,
                parameters=parameters,
                return_type=return_type,
                is_static=is_static,
                descriptor=descriptor,
                method_id=method_id,
            )
        except JNIException:
            return JavaMethod(
                name="unknown_method",
                parameters=[],
                return_type="void",
                is_static=False,
            )
        except Exception:
            return JavaMethod(
                name="unknown_method",
                parameters=[],
                return_type="void",
                is_static=False,
            )

    def _extract_field_name(self, field_obj: Any) -> str:
        """Fieldオブジェクトからフィールド名を取得"""
        try:
            name_string = self._call_object_method_with_signature_direct(
                field_obj, "getName", "()Ljava/lang/String;"
            )
            return (
                self._get_string_utf_chars(name_string)
                if name_string
                else "unknown_field"
            )
        except Exception:
            return "unknown_field"

    def _extract_field_type(self, field_obj: Any) -> str:
        """Fieldオブジェクトからフィールド型を取得"""
        try:
            type_obj = self._call_object_method_with_signature_direct(
                field_obj, "getType", "()Ljava/lang/Class;"
            )
            if type_obj:
                type_string = self._call_object_method_with_signature_direct(
                    type_obj, "getName", "()Ljava/lang/String;"
                )
                if type_string:
                    field_type = self._get_string_utf_chars(type_string)
                    # 安全性チェック: 空文字列の場合はデフォルト値
                    if not field_type or field_type.strip() == "":
                        return "Object"
                    return field_type
        except Exception:
            pass
        return "Object"

    def _extract_field_is_static(self, field_obj: Any) -> bool:
        """Fieldオブジェクトから静的フィールドかを判定"""
        try:
            obj_class = self.jni.GetObjectClass(field_obj)
            if not obj_class:
                return False
            method_id = self.jni.GetMethodID(obj_class, "getModifiers", "()I")
            if not method_id:
                return False
            modifiers = self.jni.CallIntMethod(field_obj, method_id)
            if modifiers is not None:
                # Modifier.STATICのビット演算で確認
                return bool(modifiers & STATIC_MODIFIER)
        except Exception:
            pass
        return False

    def _extract_field_info(self, field_obj: Any) -> JavaField:
        """`java.lang.reflect.Field` オブジェクトから情報を抽出"""
        try:
            name = self._extract_field_name(field_obj)

            field_type = self._extract_field_type(field_obj)
            is_static = self._extract_field_is_static(field_obj)

            return JavaField(
                name=name,
                type=field_type,
                is_static=is_static,
                descriptor=java_type_to_descriptor(field_type),
                field_id=self.jni.FromReflectedField(field_obj),
            )
        except JNIException:
            return JavaField(name="unknown_field", type="Object", is_static=False)
        except Exception:
            return JavaField(name="unknown_field", type="Object", is_static=False)

    def _extract_all_methods(self, class_obj: Any) -> List[JavaMethod]:
        """クラスのすべてのメソッド (declared + public継承) を取得"""
        all_methods: List[JavaMethod] = []
        method_signatures: set[str] = set()  # 重複排除用

        # 1. getDeclaredMethods() - そのクラスで宣言されたすべてのメソッド
        try:
            declared_methods_array = self._call_object_method_with_signature_direct(
                class_obj, "getDeclaredMethods", "()[Ljava/lang/reflect/Method;"
            )
            if declared_methods_array:
                method_count = self._get_array_length(declared_methods_array)
                for i in range(method_count):
                    method_obj = self._get_object_array_element(
                        declared_methods_array, i
                    )
                    if method_obj:
                        method_info = self._extract_method_info(method_obj)
                        signature = (
                            f"{method_info.name}({', '.join(method_info.parameters)})"
                        )
                        if signature not in method_signatures:
                            all_methods.append(method_info)
                            method_signatures.add(signature)
        except Exception:
            pass

        # 2. getMethods() - public メソッド (継承含む)
        try:
            public_methods_array = self._call_object_method_with_signature_direct(
                class_obj, "getMethods", "()[Ljava/lang/reflect/Method;"
            )
            if public_methods_array:
                method_count = self._get_array_length(public_methods_array)
                for i in range(method_count):
                    method_obj = self._get_object_array_element(public_methods_array, i)
                    if method_obj:
                        method_info = self._extract_method_info(method_obj)
                        signature = (
                            f"{method_info.name}({', '.join(method_info.parameters)})"
                        )
                        if signature not in method_signatures:
                            all_methods.append(method_info)
                            method_signatures.add(signature)
        except Exception:
            pass

        return all_methods

    def _extract_all_fields(self, class_obj: Any) -> List[JavaField]:
        """クラスのすべてのフィールド (declared + public継承) を取得"""
        all_fields: List[JavaField] = []
        field_names: set[str] = set()  # 重複排除用

        # 1. getDeclaredFields() - そのクラスで宣言されたすべてのフィールド
        try:
            declared_fields_array = self._call_object_method_with_signature_direct(
                class_obj, "getDeclaredFields", "()[Ljava/lang/reflect/Field;"
            )
            if declared_fields_array:
                field_count = self._get_array_length(declared_fields_array)
                for i in range(field_count):
                    field_obj = self._get_object_array_element(declared_fields_array, i)
                    if field_obj:
                        field_info = self._extract_field_info(field_obj)
                        if field_info.name not in field_names:
                            all_fields.append(field_info)
                            field_names.add(field_info.name)
        except Exception:
            pass

        # 2. getFields() - public フィールド (継承含む)
        try:
            public_fields_array = self._call_object_method_with_signature_direct(
                class_obj, "getFields", "()[Ljava/lang/reflect/Field;"
            )
            if public_fields_array:
                field_count = self._get_array_length(public_fields_array)
                for i in range(field_count):
                    field_obj = self._get_object_array_element(public_fields_array, i)
                    if field_obj:
                        field_info = self._extract_field_info(field_obj)
                        if field_info.name not in field_names:
                            all_fields.append(field_info)
                            field_names.add(field_info.name)
        except Exception:
            pass

        return all_fields

    def _extract_constructors(self, class_obj: Any) -> List[JavaMethod]:
        """Extract public constructors as method-like metadata."""
        constructors: List[JavaMethod] = []
        try:
            constructor_array = self._call_object_method_with_signature_direct(
                class_obj,
                "getConstructors",
                "()[Ljava/lang/reflect/Constructor;",
            )
            if not constructor_array:
                return constructors

            constructor_count = self._get_array_length(constructor_array)
            for index in range(constructor_count):
                constructor_obj = self._get_object_array_element(
                    constructor_array, index
                )
                if not constructor_obj:
                    continue
                parameters = self._extract_method_parameters(constructor_obj)
                constructors.append(
                    JavaMethod(
                        name="<init>",
                        parameters=parameters,
                        return_type="void",
                        is_static=False,
                        descriptor=method_descriptor(parameters, "void"),
                        method_id=self.jni.FromReflectedMethod(constructor_obj),
                    )
                )
        except Exception:
            return constructors
        return constructors

    def find_class(self, class_name: str) -> JavaClass:
        """クラス情報を取得 (リフレクション対応)"""
        # クラスを取得 (クラスが存在することを確認)
        jclass = self._find_class(class_name)

        # リフレクションを使用して詳細情報を取得
        methods: List[JavaMethod] = []
        fields: List[JavaField] = []
        constructors: List[JavaMethod] = []

        try:
            # jclass はすでに java.lang.Class のインスタンスなので直接使用
            class_obj = jclass
            if class_obj:
                # 完全なメソッド情報の取得 (declared + public 継承メソッド)
                methods = self._extract_all_methods(class_obj)

                # 完全なフィールド情報の取得 (declared + public継承フィールド)
                fields = self._extract_all_fields(class_obj)

                constructors = self._extract_constructors(class_obj)

        except JNIException:
            # リフレクションに失敗した場合は空
            methods = []
            fields = []
            constructors = []

        return JavaClass(
            name=class_name,
            methods=methods,
            fields=fields,
            constructors=constructors,
        )

    def discover_package_classes(self, package_name: str) -> List[str]:
        """パッケージ内クラスの動的発見 (JNI経由)"""
        discovered_classes: List[str] = []

        try:
            if self.classpath:
                from .classpath import ClasspathIndex

                index = ClasspathIndex.from_entries(self.classpath)
                discovered_classes = sorted(
                    class_name
                    for class_name in index.classes
                    if class_name.rpartition(".")[0] == package_name
                )
                if discovered_classes:
                    return discovered_classes

            # Class.forName()を使った確実なクラス発見
            discovered_classes = self._discover_classes_via_class_forname(package_name)

            if discovered_classes:
                logger.info(
                    f"Discovered {len(discovered_classes)} classes in {package_name} via JNI Class.forName"
                )
            else:
                logger.warning(
                    f"No classes discovered for package {package_name} via JNI"
                )

        except Exception as e:
            logger.error(
                f"JNI Class.forName discovery failed for package {package_name}: {e}"
            )

        return discovered_classes

    def _discover_classes_via_class_forname(self, package_name: str) -> List[str]:
        """Class.forName()とパッケージ検証を使ったクラス発見"""
        discovered_classes: List[str] = []

        try:
            # 1. パッケージが存在することを確認
            if not self._verify_package_exists(package_name):
                logger.warning(f"Package {package_name} not found in loaded packages")
                return discovered_classes

            # 2. Class.forName()で既知のクラスを探索
            discovered_classes = self._discover_classes_with_forname_patterns(
                package_name
            )

            logger.info(
                f"Discovered {len(discovered_classes)} classes in {package_name} via Class.forName"
            )

        except Exception as e:
            logger.warning(
                f"Failed to discover classes via Class.forName for {package_name}: {e}"
            )

        return discovered_classes

    def _discover_classes_from_classpath(self, package_name: str) -> List[str]:
        """クラスパスを解析してパッケージ内のクラスを発見"""
        discovered_classes: List[str] = []

        try:
            # System.getProperty("java.class.path")でクラスパス取得
            system_class = self._find_class("java/lang/System")
            if not system_class:
                raise Exception("Could not find System class")

            get_property_method = self.jni.GetStaticMethodID(
                system_class, "getProperty", "(Ljava/lang/String;)Ljava/lang/String;"
            )
            if not get_property_method:
                raise Exception("Could not find System.getProperty method")

            # "java.class.path"プロパティ取得
            class_path_key = self.jni.NewStringUTF("java.class.path")
            if not class_path_key:
                raise Exception("Could not create classpath key string")

            class_path_value = self.jni.CallStaticObjectMethod(
                system_class, get_property_method, class_path_key
            )
            if not class_path_value:
                logger.warning("Could not get java.class.path property")
                return discovered_classes

            # クラスパス文字列を取得
            class_path_str = self._get_string_utf_chars(class_path_value)
            if not class_path_str:
                return discovered_classes

            logger.debug(f"Classpath: {class_path_str}")

            # クラスパスを解析してクラスを発見
            discovered_classes = self._parse_classpath_for_package(
                class_path_str, package_name
            )

        except Exception as e:
            logger.warning(f"Failed to discover classes from classpath: {e}")

        return discovered_classes

    def _parse_classpath_for_package(
        self, class_path: str, package_name: str
    ) -> List[str]:
        """クラスパス文字列を解析してパッケージ内のクラスを発見"""
        discovered_classes: List[str] = []

        try:
            # パスセパレータを取得
            file_class = self._find_class("java/io/File")
            if not file_class:
                return discovered_classes

            # File.pathSeparatorを取得
            path_separator_field = self.jni.GetStaticFieldID(
                file_class, "pathSeparator", "Ljava/lang/String;"
            )
            if not path_separator_field:
                return discovered_classes

            path_separator_obj = self.jni.GetStaticObjectField(
                file_class, path_separator_field
            )
            if not path_separator_obj:
                return discovered_classes

            path_separator = self._get_string_utf_chars(path_separator_obj)
            if not path_separator:
                path_separator = ":"  # Unix系のデフォルト

            # クラスパスを分割して各エントリを処理
            for class_path_entry in class_path.split(path_separator):
                class_path_entry = class_path_entry.strip()
                if not class_path_entry:
                    continue

                logger.debug(f"Processing classpath entry: {class_path_entry}")

                # JARファイルかディレクトリかを判定して処理
                if class_path_entry.endswith(".jar"):
                    classes = self._discover_classes_from_jar_via_reflection(
                        class_path_entry, package_name
                    )
                    discovered_classes.extend(classes)
                else:
                    classes = self._discover_classes_from_directory_via_reflection(
                        class_path_entry, package_name
                    )
                    discovered_classes.extend(classes)

        except Exception as e:
            logger.warning(f"Failed to parse classpath: {e}")

        return discovered_classes

    def _discover_classes_from_jar_via_reflection(
        self, jar_path: str, package_name: str
    ) -> List[str]:
        """JARファイルからパッケージ内のクラスを発見 (リフレクション経由)"""
        discovered_classes: List[str] = []

        try:
            # java.util.jar.JarFileクラスを使用
            jar_file_class = self._find_class("java/util/jar/JarFile")
            if not jar_file_class:
                return discovered_classes

            # JarFileコンストラクタ
            jar_file_constructor = self.jni.GetMethodID(
                jar_file_class, "<init>", "(Ljava/lang/String;)V"
            )
            if not jar_file_constructor:
                return discovered_classes

            # JARファイルパス文字列作成
            jar_path_string = self.jni.NewStringUTF(jar_path)
            if not jar_path_string:
                return discovered_classes

            # JarFileオブジェクト作成
            jar_file_obj = self.jni.NewObject(
                jar_file_class, jar_file_constructor, jar_path_string
            )
            if not jar_file_obj:
                return discovered_classes

            # entries()メソッド取得
            entries_method = self.jni.GetMethodID(
                jar_file_class, "entries", "()Ljava/util/Enumeration;"
            )
            if not entries_method:
                return discovered_classes

            # エントリ列挙取得
            entries_enum = self.jni.CallObjectMethod(jar_file_obj, entries_method)
            if not entries_enum:
                return discovered_classes

            # エントリを反復処理してクラスを発見
            discovered_classes = self._extract_classes_from_jar_entries(
                entries_enum, package_name
            )

            # JarFileをクローズ
            try:
                close_method = self.jni.GetMethodID(jar_file_class, "close", "()V")
                if close_method:
                    self.jni.CallVoidMethod(jar_file_obj, close_method)
            except Exception:
                pass  # クローズエラーは無視

        except Exception as e:
            logger.debug(f"Failed to process JAR file {jar_path}: {e}")

        return discovered_classes

    def _discover_classes_from_directory_via_reflection(
        self, dir_path: str, package_name: str
    ) -> List[str]:
        """ディレクトリからパッケージ内のクラスを発見 (リフレクション経由)"""
        discovered_classes: List[str] = []

        try:
            # パッケージ名をディレクトリパスに変換
            package_path = package_name.replace(".", "/")
            full_package_dir = f"{dir_path}/{package_path}"

            # java.io.Fileクラスを使用
            file_class = self._find_class("java/io/File")
            if not file_class:
                return discovered_classes

            # Fileコンストラクタ
            file_constructor = self.jni.GetMethodID(
                file_class, "<init>", "(Ljava/lang/String;)V"
            )
            if not file_constructor:
                return discovered_classes

            # ディレクトリパス文字列作成
            dir_path_string = self.jni.NewStringUTF(full_package_dir)
            if not dir_path_string:
                return discovered_classes

            # Fileオブジェクト作成
            dir_file_obj = self.jni.NewObject(
                file_class, file_constructor, dir_path_string
            )
            if not dir_file_obj:
                return discovered_classes

            # exists()メソッドでディレクトリ存在確認
            exists_method = self.jni.GetMethodID(file_class, "exists", "()Z")
            if not exists_method:
                return discovered_classes

            exists = self.jni.CallBooleanMethod(dir_file_obj, exists_method)
            if not exists:
                return discovered_classes

            # listFiles()メソッドでファイル一覧取得
            list_files_method = self.jni.GetMethodID(
                file_class, "listFiles", "()[Ljava/io/File;"
            )
            if not list_files_method:
                return discovered_classes

            files_array = self.jni.CallObjectMethod(dir_file_obj, list_files_method)
            if not files_array:
                return discovered_classes

            # ファイル配列を処理してクラスファイルを検索
            discovered_classes = self._extract_classes_from_file_array(
                files_array, package_name
            )

        except Exception as e:
            logger.debug(f"Failed to process directory {dir_path}: {e}")

        return discovered_classes

    def _extract_classes_from_jar_entries(
        self, entries_enum: Any, package_name: str
    ) -> List[str]:
        """JARエントリからクラス名を抽出"""
        discovered_classes: List[str] = []

        try:
            # Enumerationクラス取得
            enum_class = self._get_object_class(entries_enum)
            if not enum_class:
                return discovered_classes

            # hasMoreElements()とnextElement()メソッド取得
            has_more_method = self.jni.GetMethodID(enum_class, "hasMoreElements", "()Z")
            next_element_method = self.jni.GetMethodID(
                enum_class, "nextElement", "()Ljava/lang/Object;"
            )
            if not has_more_method or not next_element_method:
                return discovered_classes

            package_path = package_name.replace(".", "/")

            # エントリを反復処理
            while True:
                has_more = self.jni.CallBooleanMethod(entries_enum, has_more_method)
                if not has_more:
                    break

                # JarEntry取得
                jar_entry = self.jni.CallObjectMethod(entries_enum, next_element_method)
                if not jar_entry:
                    continue

                # エントリ名取得
                entry_name_string = self._call_object_method_with_signature_direct(
                    jar_entry, "getName", "()Ljava/lang/String;"
                )
                if not entry_name_string:
                    continue

                entry_name = self._get_string_utf_chars(entry_name_string)
                if not entry_name:
                    continue

                # .classファイルでパッケージにマッチするものを抽出
                if (
                    entry_name.endswith(".class")
                    and entry_name.startswith(package_path + "/")  # noqa: W503
                    and "/"  # noqa: W503
                    not in entry_name[len(package_path) + 1 :]  # noqa: W503, E203
                ):  # サブパッケージ除外
                    class_name = entry_name[:-6].replace(
                        "/", "."
                    )  # .class除去、ドット記法変換
                    discovered_classes.append(class_name)

        except Exception as e:
            logger.warning(f"Failed to extract classes from JAR entries: {e}")

        return discovered_classes

    def _extract_classes_from_file_array(
        self, files_array: Any, package_name: str
    ) -> List[str]:
        """ファイル配列からクラス名を抽出"""
        discovered_classes: List[str] = []

        try:
            array_length = self._get_array_length(files_array)

            for i in range(array_length):
                file_obj = self._get_object_array_element(files_array, i)
                if not file_obj:
                    continue

                # ファイル名取得
                file_name_string = self._call_object_method_with_signature_direct(
                    file_obj, "getName", "()Ljava/lang/String;"
                )
                if not file_name_string:
                    continue

                file_name = self._get_string_utf_chars(file_name_string)
                if not file_name:
                    continue

                # .classファイルのみ処理
                if file_name.endswith(".class"):
                    class_simple_name = file_name[:-6]  # .class除去
                    full_class_name = f"{package_name}.{class_simple_name}"
                    discovered_classes.append(full_class_name)

        except Exception as e:
            logger.warning(f"Failed to extract classes from file array: {e}")

        return discovered_classes

    def _verify_package_exists(self, package_name: str) -> bool:
        """Package.getPackages()を使ってパッケージの存在を確認"""
        try:
            package_class = self._find_class("java/lang/Package")
            if not package_class:
                return False

            get_packages_method = self.jni.GetStaticMethodID(
                package_class, "getPackages", "()[Ljava/lang/Package;"
            )
            if not get_packages_method:
                return False

            packages_array = self.jni.CallStaticObjectMethod(
                package_class, get_packages_method
            )
            if not packages_array:
                return False

            array_length = self._get_array_length(packages_array)
            for i in range(array_length):
                package_obj = self._get_object_array_element(packages_array, i)
                if not package_obj:
                    continue

                package_name_string = self._call_object_method_with_signature_direct(
                    package_obj, "getName", "()Ljava/lang/String;"
                )
                if not package_name_string:
                    continue

                pkg_name = self._get_string_utf_chars(package_name_string)
                if pkg_name == package_name:
                    logger.info(f"Found loaded package: {package_name}")
                    return True

            return False
        except Exception as e:
            logger.warning(f"Failed to verify package existence: {e}")
            return False

    def _discover_classes_with_forname_patterns(self, package_name: str) -> List[str]:
        """Class.forName()を使って既知のパターンでクラスを発見"""
        discovered_classes: List[str] = []

        # パッケージ別の一般的なクラス名パターン
        if package_name == "java.lang":
            class_patterns = [
                "Object",
                "String",
                "System",
                "Class",
                "Thread",
                "Runtime",
                "Integer",
                "Long",
                "Double",
                "Float",
                "Boolean",
                "Byte",
                "Short",
                "Character",
                "Number",
                "Math",
                "StrictMath",
                "StringBuffer",
                "StringBuilder",
                "Throwable",
                "Exception",
                "RuntimeException",
                "Error",
                "ClassLoader",
                "Package",
                "Process",
                "ProcessBuilder",
                "SecurityManager",
                "Void",
                "Enum",
                "Deprecated",
                "Override",
                "SuppressWarnings",
                "SafeVarargs",
                "FunctionalInterface",
                "Cloneable",
                "Comparable",
                "Iterable",
                "Readable",
                "Runnable",
            ]
        elif package_name == "java.util":
            class_patterns = [
                "List",
                "ArrayList",
                "LinkedList",
                "Vector",
                "Stack",
                "Set",
                "HashSet",
                "LinkedHashSet",
                "TreeSet",
                "Map",
                "HashMap",
                "LinkedHashMap",
                "TreeMap",
                "Hashtable",
                "Collection",
                "Collections",
                "Arrays",
                "Objects",
                "Iterator",
                "ListIterator",
                "Enumeration",
                "Queue",
                "Deque",
                "ArrayDeque",
                "PriorityQueue",
                "Date",
                "Calendar",
                "GregorianCalendar",
                "TimeZone",
                "Random",
                "Scanner",
                "Timer",
                "TimerTask",
                "Properties",
                "ResourceBundle",
                "Locale",
                "UUID",
                "Currency",
                "Formatter",
                "StringTokenizer",
                "Observer",
                "Observable",
                "EventListener",
                "EventObject",
            ]
        elif package_name == "java.io":
            class_patterns = [
                "File",
                "InputStream",
                "OutputStream",
                "Reader",
                "Writer",
                "FileInputStream",
                "FileOutputStream",
                "FileReader",
                "FileWriter",
                "BufferedInputStream",
                "BufferedOutputStream",
                "BufferedReader",
                "BufferedWriter",
                "ByteArrayInputStream",
                "ByteArrayOutputStream",
                "StringReader",
                "StringWriter",
                "PrintWriter",
                "PrintStream",
                "DataInputStream",
                "DataOutputStream",
                "ObjectInputStream",
                "ObjectOutputStream",
                "RandomAccessFile",
                "FileDescriptor",
                "FilePermission",
                "IOException",
                "FileNotFoundException",
                "EOFException",
                "Serializable",
                "Externalizable",
                "ObjectInput",
                "ObjectOutput",
                "Closeable",
                "Flushable",
                "FilterInputStream",
                "FilterOutputStream",
            ]
        else:
            # その他のパッケージの場合は一般的なパターンを試す
            class_patterns = [
                "Object",
                "Exception",
                "Utils",
                "Helper",
                "Manager",
                "Factory",
                "Builder",
                "Handler",
                "Listener",
                "Event",
                "Constants",
            ]

        # Class.forName()で各パターンを試行
        for class_name in class_patterns:
            full_class_name = f"{package_name}.{class_name}"
            if self._try_load_class_by_forname(full_class_name):
                discovered_classes.append(full_class_name)

        return discovered_classes

    def _try_load_class_by_forname(self, class_name: str) -> bool:
        """Class.forName()を使ってクラスの存在を確認"""
        try:
            class_class = self._find_class("java/lang/Class")
            if not class_class:
                return False

            for_name_method = self.jni.GetStaticMethodID(
                class_class, "forName", "(Ljava/lang/String;)Ljava/lang/Class;"
            )
            if not for_name_method:
                return False

            class_name_str = self.jni.NewStringUTF(class_name)
            if not class_name_str:
                return False

            class_obj = self.jni.CallStaticObjectMethod(
                class_class, for_name_method, class_name_str
            )
            return class_obj is not None

        except Exception:
            # Class.forName()がClassNotFoundExceptionを投げる場合があるので
            # これは正常な動作として扱う
            return False

    def _try_load_class_by_name(self, class_name: str) -> Optional[Any]:
        """Class.forName()を使ってクラスをロード試行"""
        try:
            # java.lang.Classクラスを取得
            class_class = self._find_class("java/lang/Class")
            if not class_class:
                raise Exception("Could not find Class class")

            # Class.forName(String name)の静的メソッドIDを取得
            for_name_method = self.jni.GetStaticMethodID(
                class_class, "forName", "(Ljava/lang/String;)Ljava/lang/Class;"
            )
            if not for_name_method:
                raise Exception("Could not find Class.forName method")

            # クラス名の文字列を作成
            class_name_string = self.jni.NewStringUTF(class_name)
            if not class_name_string:
                raise Exception("Could not create class name string")

            # Class.forName()を呼び出し
            loaded_class = self.jni.CallStaticObjectMethod(
                class_class, for_name_method, class_name_string
            )

            # 例外が発生した場合は None を返す
            if self.jni.ExceptionCheck():
                self.jni.ExceptionClear()
                return None

            return loaded_class

        except Exception as e:
            logger.debug(f"Failed to load class {class_name}: {e}")
            return None
