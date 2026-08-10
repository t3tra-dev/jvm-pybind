from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, TypedDict

from .jvm import JVM, JavaClass, JavaField, JavaMethod


class MethodInfo(TypedDict):
    method: JavaMethod
    param_types: Optional[List[str]]
    return_type: Optional[str]


class PyiStubGenerator:
    """.pyiスタブ生成器"""

    def __init__(self, jvm: JVM, output_dir: str = "stubs"):
        self.jvm = jvm
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.class_cache: Dict[str, JavaClass] = {}

    PRIMITIVE_TYPES = {
        "void": "None",
        "boolean": "bool",
        "byte": "int",
        "short": "int",
        "int": "int",
        "long": "int",
        "float": "float",
        "double": "float",
        "char": "str",
    }

    BUILTIN_TYPES = {
        "java.lang.String": "str",
        "java.lang.Integer": "int",
        "java.lang.Boolean": "bool",
        "java.lang.Float": "float",
        "java.lang.Double": "float",
        "java.lang.Long": "int",
        "java.lang.Character": "str",
        "java.lang.Class": "Any",
        "java.lang.StringBuilder": "str",
        "java.lang.StringBuffer": "str",
    }

    def java_type_to_python_type(
        self, java_type: str, target_package: Optional[str] = None
    ) -> str:
        """Java型→Python型変換"""
        java_type = self._clean_java_type(java_type)

        if java_type in self.PRIMITIVE_TYPES:
            return self.PRIMITIVE_TYPES[java_type]

        if java_type in self.BUILTIN_TYPES:
            return self.BUILTIN_TYPES[java_type]

        if java_type.endswith("[]") or java_type.endswith(";"):
            return self._convert_array_type(java_type, target_package)

        if "<" in java_type and ">" in java_type:
            return self._convert_generic_type(java_type, target_package)

        if java_type == "java.lang.Object":
            return "Any"

        return self._convert_class_type(java_type, target_package)

    def _fix_syntax_issues(self, type_str: str) -> str:
        """型ヒント構文修正"""
        import re

        # JVM内部配列タイプ置換
        type_str = re.sub(r"^(\[B)$", "List[int]", type_str)
        type_str = re.sub(r"^(\[C)$", "List[str]", type_str)
        type_str = re.sub(r"^(\[I)$", "List[int]", type_str)
        type_str = re.sub(r"^(\[J)$", "List[int]", type_str)
        type_str = re.sub(r"^(\[F)$", "List[float]", type_str)
        type_str = re.sub(r"^(\[D)$", "List[float]", type_str)
        type_str = re.sub(r"^(\[Z)$", "List[bool]", type_str)
        type_str = re.sub(r"^(\[S)$", "List[int]", type_str)

        # コンマ後置換
        type_str = re.sub(r", (\[B)(?=\W|$)", ", List[int]", type_str)
        type_str = re.sub(r", (\[C)(?=\W|$)", ", List[str]", type_str)
        type_str = re.sub(r", (\[I)(?=\W|$)", ", List[int]", type_str)
        type_str = re.sub(r", (\[J)(?=\W|$)", ", List[int]", type_str)
        type_str = re.sub(r", (\[F)(?=\W|$)", ", List[float]", type_str)
        type_str = re.sub(r", (\[D)(?=\W|$)", ", List[float]", type_str)
        type_str = re.sub(r", (\[Z)(?=\W|$)", ", List[bool]", type_str)
        type_str = re.sub(r", (\[S)(?=\W|$)", ", List[int]", type_str)

        # 角括弧内置換
        type_str = re.sub(r"\[(\[B)\]", "[List[int]]", type_str)
        type_str = re.sub(r"\[(\[C)\]", "[List[str]]", type_str)

        # Union内置換
        type_str = re.sub(r"Union\[(\[B), ", "Union[List[int], ", type_str)
        type_str = re.sub(r"Union\[(\[C), ", "Union[List[str], ", type_str)
        type_str = re.sub(r"Union\[(\[I), ", "Union[List[int], ", type_str)
        type_str = re.sub(r"Union\[(\[J), ", "Union[List[int], ", type_str)
        type_str = re.sub(r"Union\[(\[F), ", "Union[List[float], ", type_str)
        type_str = re.sub(r"Union\[(\[D), ", "Union[List[float], ", type_str)
        type_str = re.sub(r"Union\[(\[Z), ", "Union[List[bool], ", type_str)
        type_str = re.sub(r"Union\[(\[S), ", "Union[List[int], ", type_str)

        # Union末尾置換
        type_str = re.sub(r", (\[B)\]", ", List[int]]", type_str)
        type_str = re.sub(r", (\[C)\]", ", List[str]]", type_str)
        type_str = re.sub(r", (\[I)\]", ", List[int]]", type_str)
        type_str = re.sub(r", (\[J)\]", ", List[int]]", type_str)
        type_str = re.sub(r", (\[F)\]", ", List[float]]", type_str)
        type_str = re.sub(r", (\[D)\]", ", List[float]]", type_str)
        type_str = re.sub(r", (\[Z)\]", ", List[bool]]", type_str)
        type_str = re.sub(r", (\[S)\]", ", List[int]]", type_str)

        # Union構文修正
        if "Union[" in type_str and ", arg" in type_str:
            if "], arg" in type_str:
                type_str = type_str.split("], arg")[0] + "]"

        # 配列構文修正
        if type_str.endswith(", arg"):
            type_str = type_str.split(", arg")[0]

        # Union括弧修正
        if type_str.startswith("Union[") and type_str.count("[") > type_str.count("]"):
            missing_brackets = type_str.count("[") - type_str.count("]")
            type_str += "]" * missing_brackets

        return type_str

    def _convert_array_type(self, java_type: str, target_package: Optional[str]) -> str:
        """配列型変換"""
        if java_type.endswith(";[") or java_type.endswith(";]"):
            element_type = java_type.replace(";[", "").replace(";]", "")
        elif java_type.endswith("[]"):
            element_type = java_type[:-2]
        elif java_type.endswith(";"):
            element_type = java_type[:-1]
        else:
            element_type = java_type

        python_element_type = self.java_type_to_python_type(
            element_type, target_package
        )
        return f"List[{python_element_type}]"

    def _convert_generic_type(
        self, java_type: str, target_package: Optional[str]
    ) -> str:
        """ジェネリック型変換"""
        base_type = java_type.split("<")[0]
        return self.java_type_to_python_type(base_type, target_package)

    def _clean_java_type(self, java_type: str) -> str:
        """Java型クリーンアップ"""
        java_type = java_type.rstrip(";")
        java_type = java_type.replace(";[", "[")
        java_type = java_type.replace(";]", "]")
        java_type = java_type.strip()

        return java_type

    def _convert_class_type(self, java_type: str, target_package: Optional[str]) -> str:
        """クラス型変換"""
        java_type = self._clean_java_type(java_type)

        if target_package and java_type.startswith(target_package + "."):
            class_name = java_type.split(".")[-1]
            return self.sanitize_identifier(class_name)

        if "." in java_type:
            class_name = java_type.split(".")[-1]
            return self.sanitize_identifier(class_name)

        return self.sanitize_identifier(java_type) if java_type else "Any"

    def sanitize_identifier(self, name: str) -> str:
        """識別子正規化"""
        # Python予約語のリスト
        PYTHON_KEYWORDS = {
            "and",
            "as",
            "assert",
            "break",
            "class",
            "continue",
            "def",
            "del",
            "elif",
            "else",
            "except",
            "exec",
            "finally",
            "for",
            "from",
            "global",
            "if",
            "import",
            "in",
            "is",
            "lambda",
            "not",
            "or",
            "pass",
            "print",
            "raise",
            "return",
            "try",
            "while",
            "with",
            "yield",
            "None",
            "True",
            "False",
        }

        name = name.rstrip(";")
        name = name.replace("$", "_")
        if name in PYTHON_KEYWORDS:
            name = name + "_"

        return name

    def create_union_type(self, types: List[str]) -> str:
        """Union型作成"""
        unique_types = sorted(set(types))

        if len(unique_types) == 1:
            return unique_types[0]

        if "Any" in unique_types:
            return "Any"

        return f"Union[{', '.join(unique_types)}]"

    def normalize_method_signature(
        self, method: JavaMethod, target_package: Optional[str] = None
    ) -> Tuple[str, List[str], str]:
        """メソッドシグネチャ正規化"""
        sanitized_name = self.sanitize_identifier(method.name)
        param_types = [
            self.java_type_to_python_type(param, target_package)
            for param in method.parameters
        ]
        return_type = self.java_type_to_python_type(method.return_type, target_package)
        return sanitized_name, param_types, return_type

    def deduplicate_overloads(
        self, overloads: List[JavaMethod], target_package: Optional[str] = None
    ) -> List[MethodInfo]:
        """オーバーロード重複排除"""
        if len(overloads) <= 1:
            return (
                [MethodInfo(method=overloads[0], param_types=None, return_type=None)]
                if overloads
                else []
            )

        param_count_groups: Dict[int, List[JavaMethod]] = {}
        for method in overloads:
            param_count = len(method.parameters)
            if param_count not in param_count_groups:
                param_count_groups[param_count] = []
            param_count_groups[param_count].append(method)

        deduplicated = []

        for param_count, methods in param_count_groups.items():
            if len(methods) == 1:
                deduplicated.append(
                    MethodInfo(method=methods[0], param_types=None, return_type=None)
                )
            else:
                # パラメータ数同一メソッドマージ
                all_param_types = []
                all_return_types = []

                for method in methods:
                    _, param_types, return_type = self.normalize_method_signature(
                        method, target_package
                    )
                    all_param_types.append(param_types)
                    all_return_types.append(return_type)

                # パラメータ位置Union型作成
                merged_param_types = []
                for i in range(param_count):
                    param_types_at_pos = [types[i] for types in all_param_types]
                    merged_param_types.append(
                        self.create_union_type(param_types_at_pos)
                    )

                # 戻り値Union型化
                merged_return_type = self.create_union_type(all_return_types)

                deduplicated.append(
                    MethodInfo(
                        method=methods[0],
                        param_types=merged_param_types,
                        return_type=merged_return_type,
                    )
                )

        return deduplicated

    def generate_deduplicated_method_signatures(
        self, overloads: List[JavaMethod], target_package: Optional[str] = None
    ) -> List[str]:
        """メソッドシグネチャ重複排除生成"""
        deduplicated = self.deduplicate_overloads(overloads, target_package)

        if len(deduplicated) == 1:
            method_info = deduplicated[0]
            method = method_info["method"]

            return [
                self.generate_method_signature(
                    method,
                    target_package,
                    method_info["param_types"],
                    method_info["return_type"],
                )
            ]
        else:
            signatures = []
            for i, method_info in enumerate(deduplicated):
                method = method_info["method"]

                if i < len(deduplicated) - 1:
                    signatures.append("    @overload")

                signature = self.generate_method_signature(
                    method,
                    target_package,
                    method_info["param_types"],
                    method_info["return_type"],
                )
                signatures.append(signature)

            return signatures

    def get_java_class(self, class_name: str) -> JavaClass:
        """Javaクラスキャッシュ取得"""
        if class_name not in self.class_cache:
            try:
                self.class_cache[class_name] = self.jvm.find_class(
                    class_name.replace(".", "/")
                )
            except Exception:
                self.class_cache[class_name] = JavaClass(
                    name=class_name, methods=[], fields=[]
                )
        return self.class_cache[class_name]

    def collect_dependencies(
        self, java_class: JavaClass, target_package: Optional[str] = None
    ) -> Set[str]:
        """依存関係収集"""
        dependencies = set()

        # フィールド依存
        for field in java_class.fields:
            dep = self.extract_dependency(field.type, target_package)
            if dep:
                dependencies.add(dep)

        # メソッド依存
        for method in java_class.methods:
            # 戻り値
            dep = self.extract_dependency(method.return_type, target_package)
            if dep:
                dependencies.add(dep)

            # パラメータ
            for param_type in method.parameters:
                dep = self.extract_dependency(param_type, target_package)
                if dep:
                    dependencies.add(dep)

        return dependencies

    def extract_dependency(
        self, java_type: str, target_package: Optional[str] = None
    ) -> Optional[str]:
        """依存関係抽出"""
        # プリミティブ型スキップ
        if java_type in self.PRIMITIVE_TYPES:
            return None

        # 組み込みスキップ
        if java_type in self.BUILTIN_TYPES:
            return None

        # 配列型
        if java_type.endswith("[]"):
            return self.extract_dependency(java_type[:-2], target_package)

        # ジェネリック型
        if "<" in java_type and ">" in java_type:
            base_type = java_type.split("<")[0]
            return self.extract_dependency(base_type, target_package)

        # ターゲットパッケージ依存のみ
        if target_package and java_type.startswith(target_package + "."):
            return java_type

        # 一般的Javaパッケージ含む
        if java_type.startswith(("java.io.", "java.util.")):
            return java_type

        return None

    def _build_param_string(
        self, param_types: List[str], is_static: bool = False
    ) -> str:
        """パラメータ文字列作成"""
        params = [] if is_static else ["self"]

        for i, param_type in enumerate(param_types):
            param_name = "x" if i == 0 else f"arg{i}"
            clean_param_type = self._fix_syntax_issues(param_type)
            params.append(f"{param_name}: {clean_param_type}")

        return ", ".join(params)

    def generate_method_signature(
        self,
        method: JavaMethod,
        target_package: Optional[str] = None,
        custom_types: Optional[List[str]] = None,
        custom_return_type: Optional[str] = None,
    ) -> str:
        """メソッドシグネチャ生成"""
        if custom_types is not None:
            param_types = custom_types
        else:
            param_types = [
                self.java_type_to_python_type(param, target_package)
                for param in method.parameters
            ]

        if custom_return_type is not None:
            return_type = custom_return_type
        else:
            return_type = self.java_type_to_python_type(
                method.return_type, target_package
            )
        return_type = self._fix_syntax_issues(return_type)

        sanitized_name = self.sanitize_identifier(method.name)
        param_str = self._build_param_string(param_types, method.is_static)

        if method.is_static:
            return (
                f"    @staticmethod\n"
                f"    def {sanitized_name}({param_str}) -> {return_type}: ..."
            )
        else:
            return f"    def {sanitized_name}({param_str}) -> {return_type}: ..."

    def generate_field_signature(
        self, field: JavaField, target_package: Optional[str] = None
    ) -> str:
        """フィールドシグネチャ生成"""
        python_type = self.java_type_to_python_type(field.type, target_package)
        python_type = self._fix_syntax_issues(python_type)
        sanitized_name = self.sanitize_identifier(field.name)
        suffix = "  # static" if field.is_static else ""
        return f"    {sanitized_name}: {python_type}{suffix}"

    def generate_class_stub(
        self, java_class: JavaClass, target_package: Optional[str] = None
    ) -> str:
        """クラススタブ生成"""
        class_name = java_class.name.replace("/", ".").split(".")[-1]
        sanitized_class_name = self.sanitize_identifier(class_name)

        lines = [f"class {sanitized_class_name}:"]

        if java_class.fields:
            for field in java_class.fields:
                lines.append(self.generate_field_signature(field, target_package))
            lines.append("")

        if java_class.constructors:
            constructor_methods = [
                JavaMethod(
                    name="__init__",
                    parameters=constructor.parameters,
                    return_type="void",
                    is_static=False,
                    descriptor=constructor.descriptor,
                )
                for constructor in java_class.constructors
            ]
            lines.extend(
                self.generate_deduplicated_method_signatures(
                    constructor_methods, target_package
                )
            )
            lines.append("")

        method_groups = self._group_methods_by_name(java_class.methods)

        if method_groups:
            for overloads in method_groups.values():
                method_signatures = self.generate_deduplicated_method_signatures(
                    overloads, target_package
                )
                lines.extend(method_signatures)
                lines.append("")

        has_members = bool(
            java_class.methods or java_class.fields or java_class.constructors
        )
        if not has_members:
            lines.append("    pass")

        return "\n".join(lines)

    def _group_methods_by_name(
        self, methods: List[JavaMethod]
    ) -> Dict[str, List[JavaMethod]]:
        groups: Dict[str, List[JavaMethod]] = {}
        for method in methods:
            sanitized_name = self.sanitize_identifier(method.name)
            if sanitized_name not in groups:
                groups[sanitized_name] = []
            groups[sanitized_name].append(method)
        return groups

    def generate_package_stub(
        self, package_name: str, class_names: Optional[List[str]] = None
    ) -> Path:
        """パッケージスタブ生成"""
        if class_names is None:
            class_names = self._discover_package_classes(package_name)

        all_classes, external_dependencies = self._collect_all_dependencies(
            package_name, class_names
        )

        stub_content = self._generate_package_stub_content(
            package_name, all_classes, external_dependencies
        )

        return self._write_package_stub(package_name, stub_content)

    def _collect_all_dependencies(
        self, package_name: str, class_names: List[str]
    ) -> Tuple[Set[str], Set[str]]:
        """全依存関係収集"""
        all_classes = set(class_names)
        processed_classes: Set[str] = set()
        external_dependencies = set()

        # 再帰的依存収集
        while all_classes - processed_classes:
            class_name = next(iter(all_classes - processed_classes))
            processed_classes.add(class_name)

            try:
                java_class = self.get_java_class(class_name)
                dependencies = self.collect_dependencies(java_class, package_name)

                for dep in dependencies:
                    if dep.startswith(package_name + ".") and dep not in all_classes:
                        all_classes.add(dep)
                    elif dep:
                        external_dependencies.add(dep)
            except Exception:
                continue

        # 外部依存追加
        for ext_dep in external_dependencies.copy():
            if ext_dep not in all_classes:
                try:
                    self.get_java_class(ext_dep)
                    all_classes.add(ext_dep)
                except Exception:
                    pass

        return all_classes, external_dependencies

    def _generate_package_stub_content(
        self, package_name: str, all_classes: Set[str], external_dependencies: Set[str]
    ) -> str:
        """スタブ内容生成"""
        lines = [
            "from __future__ import annotations",
            "",
            "from typing import Any, List, Union, overload",
            "",
        ]

        # パッケージクラス優先
        package_classes = sorted(
            [cls for cls in all_classes if cls.startswith(package_name + ".")]
        )
        all_classes_to_generate = package_classes + sorted(external_dependencies)

        for class_name in all_classes_to_generate:
            try:
                java_class = self.get_java_class(class_name)
                class_stub = self.generate_class_stub(java_class, package_name)
                lines.append(class_stub)
                lines.append("")
            except Exception as e:
                print(f"Failed to generate stub for {class_name}: {e}")
                if class_name in external_dependencies:
                    lines.extend(self._create_simple_stub(class_name))
                continue

        return "\n".join(lines)

    def _create_simple_stub(self, class_name: str) -> List[str]:
        """シンプルスタブ作成"""
        simple_name = class_name.split(".")[-1]
        sanitized_name = self.sanitize_identifier(simple_name)
        return [f"class {sanitized_name}:", "    pass", ""]

    def _write_package_stub(self, package_name: str, stub_content: str) -> Path:
        """スタブファイル書き込み"""
        package_parts = package_name.split(".")
        target_dir = self.output_dir.joinpath(*package_parts[:-1])
        target_dir.mkdir(parents=True, exist_ok=True)

        stub_file = target_dir / f"{package_parts[-1]}.pyi"
        stub_file.write_text(stub_content)

        print(f"Generated package stub: {stub_file}")
        return stub_file

    def generate_package_init(self, classes: List[str]) -> str:
        """__init__.pyi生成"""
        lines = ["from __future__ import annotations", ""]

        # 全クラスインポート
        for class_name in classes:
            lines.append(f"from .{class_name} import {class_name}")

        lines.extend(["", "__all__ = ["])

        for class_name in classes:
            lines.append(f'    "{class_name}",')

        lines.append("]")

        return "\n".join(lines)

    def _discover_package_classes(self, package_name: str) -> List[str]:
        """パッケージクラス動的発見"""
        discovered_classes = []

        try:
            discovered_classes = self.jvm.discover_package_classes(package_name)

            if discovered_classes:
                print(
                    f"Dynamically discovered {len(discovered_classes)} classes for package {package_name} via JNI"
                )
            else:
                print(
                    f"Warning: No classes discovered for package {package_name} via JNI"
                )

        except Exception as e:
            print(
                f"Failed to dynamically discover classes for {package_name} via JNI: {e}"
            )

        return discovered_classes

    def generate_stub_for_class(self, class_name: str) -> None:
        """クラススタブ生成"""
        try:
            java_class = self.jvm.find_class(class_name.replace(".", "/"))
            stub_content = self.generate_class_stub(java_class)

            package_parts = class_name.split(".")
            class_simple_name = package_parts[-1]
            package_path = "/".join(package_parts[:-1])

            target_dir = self.output_dir / package_path
            target_dir.mkdir(parents=True, exist_ok=True)

            stub_file = target_dir / f"{class_simple_name}.pyi"
            stub_file.write_text(stub_content)

            self._update_package_init(target_dir, class_simple_name)

        except Exception as e:
            print(f"Failed to generate stub for {class_name}: {e}")

    def _update_package_init(self, target_dir: Path, class_simple_name: str) -> None:
        """__init__.pyi更新"""
        init_file = target_dir / "__init__.pyi"
        if init_file.exists():
            content = init_file.read_text()
            import_line = f"from .{class_simple_name} import {class_simple_name}"

            if import_line not in content:
                self._add_import_to_existing_init(init_file, content, class_simple_name)
        else:
            init_content = self.generate_package_init([class_simple_name])
            init_file.write_text(init_content)

    def _add_import_to_existing_init(
        self, init_file: Path, content: str, class_simple_name: str
    ) -> None:
        """インポート追加"""
        lines = content.split("\n")
        import_section_end = 0

        for i, line in enumerate(lines):
            if line.startswith("from .") and " import " in line:
                import_section_end = i + 1
            elif line.startswith("__all__"):
                break

        lines.insert(
            import_section_end,
            f"from .{class_simple_name} import {class_simple_name}",
        )

        # __all__更新
        for i, line in enumerate(lines):
            if line.strip() == "]" and i > 0 and "__all__" in lines[i - 2]:
                lines.insert(i, f'    "{class_simple_name}",')
                break

        init_file.write_text("\n".join(lines))

    def generate_common_stubs(self) -> None:
        """共通スタブ生成"""
        # 共通パッケージスタブ生成
        common_packages = ["java.lang", "java.util", "java.io"]

        for package_name in common_packages:
            try:
                self.generate_package_stub(package_name)
                print(f"Generated stubs for package {package_name}")
            except Exception as e:
                print(f"Failed to generate stubs for package {package_name}: {e}")

        print(f"Generated stubs in {self.output_dir}")

    def generate_stub_for_package(self, package_name: str) -> None:
        """パッケージスタブ生成"""
        print(f"Package stub generation for {package_name} not implemented yet")

    def generate_stub_from_usage(self, class_name: str) -> None:
        """使用ベーススタブ生成"""
        self.generate_stub_for_class(class_name)
        print(f"Generated stub for {class_name} based on usage")
