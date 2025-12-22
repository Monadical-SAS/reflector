def assert_not_none[T](value: T | None, message: str = "Value is None") -> T:
    if value is None:
        raise ValueError(message)
    return value
