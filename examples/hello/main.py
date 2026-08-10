import jvm  # noqa: I001, F401

from mypkg import Hello  # pyright: ignore[reportMissingModuleSource]

print(Hello.greet("World"))
