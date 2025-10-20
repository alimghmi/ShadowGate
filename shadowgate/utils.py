import json
import random
from importlib.resources import files
from pathlib import Path
from typing import List

from .entities.proxy import Proxy, _parse_from_url


def _read_file(path: str | Path):
    file = files("shadowgate") / str(path)
    if not file.is_file():
        raise FileNotFoundError(f"{path} not found.")

    return file.read_text(encoding="utf-8")


class WordsListLoader:

    def __init__(self, wordslists_path: Path) -> None:
        self.wordslist_path = wordslists_path

    def load(self) -> List:
        if self.wordslist_path.suffix == ".json":
            return json.loads(_read_file(self.wordslist_path))
        elif self.wordslist_path.suffix == ".txt":
            return [line.strip() for line in open(self.wordslist_path, "r").readlines()]
        else:
            raise ValueError("Unsupported file extension for the wordslist.")


class URLBuilder:

    def __init__(self, url: str, wordslist: Path | List[str]) -> None:
        self.url = url
        if isinstance(wordslist, list):
            self.wordslist = wordslist
        else:
            self.wordslist = WordsListLoader(wordslist).load()

    def compile(self) -> List[str]:
        urls = []
        for path in self.wordslist:
            url = self._process_url(path)
            urls.append(url)

        return urls

    def _process_url(self, path: str) -> str:
        url = self.url.lower()

        if url.endswith("/"):
            url = url[:-1]

        scheme = ""
        for _p in ["http://", "https://"]:
            if url.startswith(_p):
                scheme = _p
                url = url.replace(_p, "")
                break
        else:
            raise ValueError("URL must start with an scheme, http:// or https://.")

        res = f"{scheme}{path.replace("[url]", url)}"
        return res


class UserAgent:

    def __init__(self, useragents_path: Path) -> None:
        self.useragents_path = useragents_path
        self.uas = self._load_uas()

    @property
    def _random(self) -> str:
        return random.choice(self.uas)

    def _load_uas(self) -> List[str]:
        return json.loads(_read_file(self.useragents_path))


class ProxiesLoader:

    def __init__(self, proxies_path: Path) -> None:
        self.proxies_path = proxies_path

    def load(self) -> List:
        if not (self.proxies_path.exists() and self.proxies_path.is_file()):
            raise FileNotFoundError(f"{self.proxies_path} not found.")

        if self.proxies_path.suffix == ".json":
            return json.load(open(self.proxies_path, "r"))
        elif self.proxies_path.suffix == ".txt":
            return [line.strip() for line in open(self.proxies_path, "r").readlines()]
        else:
            raise ValueError("Unsupported file extension for the wordslist.")


class ProxyHandler:

    def __init__(self, proxies: Path | List[str]) -> None:
        self.proxies: List[Proxy] = []
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
