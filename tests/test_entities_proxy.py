from shadowgate.entities.proxy import Proxy, _parse_from_url


def test_parse_from_url_valid_and_stringify():
    p = _parse_from_url("http://user:pass@host:8080")
    assert isinstance(p, Proxy)
    assert str(p) == "http://user:pass@host:8080"
    p2 = _parse_from_url("socks5://host:9050")
    assert str(p2) == "socks5://host:9050"


def test_parse_from_url_invalid():
    assert _parse_from_url("notaurl") is False
    assert _parse_from_url("http://") is False


def test_proxy_str_handles_no_auth():
    p = Proxy(scheme="http://", host="host", port=8080, username=None, password=None)
    assert str(p) == "http://host:8080"
