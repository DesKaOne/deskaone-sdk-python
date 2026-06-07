from deskaone_sdk.network.handlers.http import (
    find_header,
    parse_status_code,
    sanitize_header_for_error,
)


def test_http_handler_helpers():
    headers = b"HTTP/1.1 407 Proxy Authentication Required\r\nProxy-Authenticate: Basic\r\nProxy-Authorization: secret\r\n\r\n"
    assert parse_status_code(headers) == 407
    assert find_header(headers, "proxy-authenticate") == "Basic"
    assert "<redacted>" in sanitize_header_for_error(headers)
    assert "secret" not in sanitize_header_for_error(headers)
