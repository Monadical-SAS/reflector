from typing import NoReturn


def assert_exhaustiveness(x: NoReturn) -> NoReturn:
    """Provide an assertion at type-check time that this function is never called."""
    raise AssertionError(f"Invalid value: {x!r}")


def absurd(x: NoReturn) -> NoReturn:
    return assert_exhaustiveness(x)
