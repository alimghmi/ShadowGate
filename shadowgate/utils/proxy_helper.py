import json
import random
from pathlib import Path

from ..entities.proxy import Proxy, _parse_from_url


class ProxiesLoader:
    def __init__(self, proxies_path: Path) -> None:
        self.proxies_path = proxies_path

    def load(self) -> list:
        if not (self.proxies_path.exists() and self.proxies_path.is_file()):
            raise FileNotFoundError(f"{self.proxies_path} not found.")

        if self.proxies_path.suffix == ".json":
            return json.load(open(self.proxies_path))
        elif self.proxies_path.suffix == ".txt":
            return [line.strip() for line in open(self.proxies_path).readlines()]
        else:
            raise ValueError("Unsupported file extension for the wordslist.")


class ProxyHandler:
    def __init__(self, proxies: Path | list[str]) -> None:
        self.proxies: list[Proxy] = []
        if isinstance(proxies, list):
            self.proxies_url = proxies
        else:
            self.proxies_url = ProxiesLoader(proxies).load()

        self.get_proxies()

    def get_proxies(self):
        for url in self.proxies_url:
            _proxy = _parse_from_url(url)
            if _proxy:
                self.proxies.append(_proxy)  # type: ignore

    def remove_proxy(self, proxy: Proxy) -> bool:
        if proxy in self.proxies:
            self.proxies.remove(proxy)
            return True

        return False

    @property
    def random_proxy(self):
        return random.choice(self.proxies).url

    @property
    def is_available(self):
        return bool(len(self.proxies))
