from typing import Annotated, TypeVar

from pydantic import Field, TypeAdapter, constr

T_NotNone = TypeVar("T_NotNone")


def assert_not_none(
    value: T_NotNone | None, message: str = "Value is None"
) -> T_NotNone:
    if value is None:
        raise ValueError(message)
    return value


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


T_Str = TypeVar("T_Str", bound=str)


def assert_equal(s1: T_Str, s2: T_Str) -> T_Str:
    if s1 != s2:
        raise ValueError(f"assert_equal: {s1} != {s2}")
    return s1


def assert_non_none_and_non_empty(
    value: str | None, error: str | None = None
) -> NonEmptyString:
    return parse_non_empty_string(
        assert_not_none(value, error or "Value is None"), error
    )
