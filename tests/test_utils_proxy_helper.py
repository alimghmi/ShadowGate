import json
from pathlib import Path

from shadowgate.utils.proxy_helper import ProxiesLoader, ProxyHandler


def test_proxies_loader_from_json_and_txt(tmp_path: Path):
    jp = tmp_path / "proxies.json"
    jp.write_text(json.dumps(["http://h:1", "socks5://h:2"]))
    loader = ProxiesLoader(proxies_path=jp)
    assert len(loader.load()) == 2

    tp = tmp_path / "proxies.txt"
    tp.write_text("http://h:1\nsocks5://h:2\n")
    loader = ProxiesLoader(proxies_path=tp)
    assert len(loader.load()) == 2


def test_proxy_handler_add_remove_random_and_availability(tmp_path: Path):
    tp = tmp_path / "p.txt"
    tp.write_text("http://h:1\nhttp://h:2\n")
    handler = ProxyHandler(proxies=tp)
    assert handler.is_available
    assert handler.random_proxy.startswith("http")
