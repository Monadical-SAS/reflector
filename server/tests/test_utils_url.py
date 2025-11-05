"""Tests for URL utility functions."""

from reflector.utils.url import add_query_param


class TestAddQueryParam:
    """Test the add_query_param function."""

    def test_add_param_to_url_without_query(self):
        """Should add query param with ? to URL without existing params."""
        url = "https://example.com/room"
        result = add_query_param(url, "t", "token123")
        assert result == "https://example.com/room?t=token123"

    def test_add_param_to_url_with_existing_query(self):
        """Should add query param with & to URL with existing params."""
        url = "https://example.com/room?existing=param"
        result = add_query_param(url, "t", "token123")
        assert result == "https://example.com/room?existing=param&t=token123"

    def test_add_param_to_url_with_multiple_existing_params(self):
        """Should add query param to URL with multiple existing params."""
        url = "https://example.com/room?param1=value1&param2=value2"
        result = add_query_param(url, "t", "token123")
        assert (
            result == "https://example.com/room?param1=value1&param2=value2&t=token123"
        )

    def test_add_param_with_special_characters(self):
        """Should properly encode special characters in param value."""
        url = "https://example.com/room"
        result = add_query_param(url, "name", "hello world")
        assert result == "https://example.com/room?name=hello+world"

    def test_add_param_to_url_with_fragment(self):
        """Should preserve URL fragment when adding query param."""
        url = "https://example.com/room#section"
        result = add_query_param(url, "t", "token123")
        assert result == "https://example.com/room?t=token123#section"

    def test_add_param_to_url_with_query_and_fragment(self):
        """Should preserve fragment when adding param to URL with existing query."""
        url = "https://example.com/room?existing=param#section"
        result = add_query_param(url, "t", "token123")
        assert result == "https://example.com/room?existing=param&t=token123#section"

    def test_add_param_overwrites_existing_param(self):
        """Should overwrite existing param with same name."""
        url = "https://example.com/room?t=oldtoken"
        result = add_query_param(url, "t", "newtoken")
        assert result == "https://example.com/room?t=newtoken"

    def test_url_without_scheme(self):
        """Should handle URLs without scheme (relative URLs)."""
        url = "/room/path"
        result = add_query_param(url, "t", "token123")
        assert result == "/room/path?t=token123"

    def test_empty_url(self):
        """Should handle empty URL."""
        url = ""
        result = add_query_param(url, "t", "token123")
        assert result == "?t=token123"
