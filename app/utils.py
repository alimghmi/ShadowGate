import json
import random
from typing import List


class WordsListLoader:

    def __init__(self, wordslists_path: str) -> None:
        self.wordslist_path = wordslists_path

    def load(self) -> List:
        if self.wordslist_path.endswith(".json"):
            return json.load(open(self.wordslist_path, "r"))
        elif self.wordslist_path.endswith(".txt"):
            return [line.strip() for line in open(self.wordslist_path, "r").readlines()]
        else:
            raise ValueError("Unsupported file extension for the wordslist.")


class URLBuilder:

    def __init__(self, url: str, wordslists_path: str) -> None:
        self.url = url
        self.wordslist = WordsListLoader(wordslists_path).load()

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

        protocol = ""
        for _p in ["http://", "https://"]:
            if url.startswith(_p):
                protocol = _p
                url = url.replace(_p, "")
                break
        else:
            raise ValueError("URL must start with a protocol, http:// or https://.")

        res = f"{protocol}{path.replace("[url]", url)}"
        return res


class UserAgent:

    def __init__(self, useragents_path: str) -> None:
        self.uas = self._load_uas(useragents_path)

    @property
    def _random(self) -> str:
        return random.choice(self.uas)

    def _load_uas(self, useragents_path: str) -> List[str]:
        return json.load(open(useragents_path, "r"))
