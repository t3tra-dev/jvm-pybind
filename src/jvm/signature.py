from __future__ import annotations

from typing import Iterable

PRIMITIVE_DESCRIPTORS = {
    "void": "V",
    "boolean": "Z",
    "byte": "B",
    "char": "C",
    "short": "S",
    "int": "I",
    "long": "J",
    "float": "F",
    "double": "D",
}
DESCRIPTOR_PRIMITIVES = {value: key for key, value in PRIMITIVE_DESCRIPTORS.items()}


def java_type_to_descriptor(java_type: str) -> str:
    """Convert a reflection/source Java type name to a JNI descriptor."""
    normalized = java_type.strip()
    if normalized in PRIMITIVE_DESCRIPTORS:
        return PRIMITIVE_DESCRIPTORS[normalized]

    if normalized.startswith("["):
        return normalized.replace(".", "/")

    dimensions = 0
    while normalized.endswith("[]"):
        dimensions += 1
        normalized = normalized[:-2]

    if dimensions:
        return "[" * dimensions + java_type_to_descriptor(normalized)

    if normalized.startswith("L") and normalized.endswith(";"):
        return normalized.replace(".", "/")

    return f"L{normalized.replace('.', '/')};"


def method_descriptor(parameter_types: Iterable[str], return_type: str) -> str:
    parameters = "".join(java_type_to_descriptor(item) for item in parameter_types)
    return f"({parameters}){java_type_to_descriptor(return_type)}"


def is_primitive(java_type: str) -> bool:
    return java_type in PRIMITIVE_DESCRIPTORS and java_type != "void"


def is_reference(java_type: str) -> bool:
    return not is_primitive(java_type) and java_type != "void"


def is_array(java_type: str) -> bool:
    normalized = java_type.strip()
    return normalized.startswith("[") or normalized.endswith("[]")


def array_component_type(java_type: str) -> str:
    descriptor = java_type_to_descriptor(java_type)
    if not descriptor.startswith("["):
        raise ValueError(f"Not a Java array type: {java_type}")

    component = descriptor[1:]
    if component in DESCRIPTOR_PRIMITIVES:
        return DESCRIPTOR_PRIMITIVES[component]
    if component.startswith("["):
        return component.replace("/", ".")
    if component.startswith("L") and component.endswith(";"):
        return component[1:-1].replace("/", ".")
    raise ValueError(f"Unsupported Java array descriptor: {descriptor}")
