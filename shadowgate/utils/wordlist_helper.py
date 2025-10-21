import json
from pathlib import Path
from typing import List

from .misc import _read_file


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
