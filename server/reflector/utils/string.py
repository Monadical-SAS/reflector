from typing import Annotated

from pydantic import Field, TypeAdapter, constr

NonEmptyStringBase = constr(min_length=1, strip_whitespace=False)
NonEmptyString = Annotated[
    NonEmptyStringBase,
    Field(description="A non-empty string", min_length=1),
]
non_empty_string_adapter = TypeAdapter(NonEmptyString)


def parse_non_empty_string(s: str) -> NonEmptyString:
    return non_empty_string_adapter.validate_python(s)


def try_parse_non_empty_string(s: str) -> NonEmptyString | None:
    if not s:
        return None
    return parse_non_empty_string(s)
