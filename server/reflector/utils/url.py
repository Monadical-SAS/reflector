"""URL manipulation utilities."""

from urllib.parse import parse_qs, urlencode, urlparse, urlunparse


def add_query_param(url: str, key: str, value: str) -> str:
    """
    Add or update a query parameter in a URL.

    Properly handles URLs with or without existing query parameters,
    preserving fragments and encoding special characters.

    Args:
        url: The URL to modify
        key: The query parameter name
        value: The query parameter value

    Returns:
        The URL with the query parameter added or updated

    Examples:
        >>> add_query_param("https://example.com/room", "t", "token123")
        'https://example.com/room?t=token123'

        >>> add_query_param("https://example.com/room?existing=param", "t", "token123")
        'https://example.com/room?existing=param&t=token123'
    """
    parsed = urlparse(url)

    query_params = parse_qs(parsed.query, keep_blank_values=True)

    query_params[key] = [value]

    new_query = urlencode(query_params, doseq=True)

    new_parsed = parsed._replace(query=new_query)
    return urlunparse(new_parsed)
