from typing import Annotated, TypeVar

from pydantic import Field, TypeAdapter, constr

NonEmptyStringBase = constr(min_length=1, strip_whitespace=False)
NonEmptyString = Annotated[
    NonEmptyStringBase,
    Field(description="A non-empty string", min_length=1),
]
non_empty_string_adapter = TypeAdapter(NonEmptyString)


def parse_non_empty_string(s: str, error: str | None = None) -> NonEmptyString:
    try:
        return non_empty_string_adapter.validate_python(s)
    except Exception as e:
        raise ValueError(f"{e}: {error}" if error else e) from e


def try_parse_non_empty_string(s: str) -> NonEmptyString | None:
    if not s:
        return None
    return parse_non_empty_string(s)


T = TypeVar("T", bound=str)


def assert_equal[T](s1: T, s2: T) -> T:
    if s1 != s2:
        raise ValueError(f"assert_equal: {s1} != {s2}")
    return s1
