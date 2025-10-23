import json
from pathlib import Path

from .misc import _read_file


class WordsListLoader:
    WORDSLIST_PATH = Path("data/wordslist.json")

    def __init__(self, wordslists_path: Path) -> None:
        self.wordslist_path = wordslists_path

    def load(self) -> list:
        if self.wordslist_path == self.WORDSLIST_PATH:
            return json.loads(_read_file(self.wordslist_path))

        if self.wordslist_path.suffix == ".json":
            return json.load(open(self.wordslist_path))
        elif self.wordslist_path.suffix == ".txt":
            return [line.strip() for line in open(self.wordslist_path).readlines()]
        else:
            raise ValueError("Unsupported file extension for the wordslist.")


class URLBuilder:
    def __init__(self, url: str, wordslist: Path | list[str]) -> None:
        self.url = url
        if isinstance(wordslist, list):
            self.wordslist = wordslist
        else:
            self.wordslist = WordsListLoader(wordslist).load()

    def compile(self) -> list[str]:
        urls = []
        for path in self.wordslist:
            url = self._process_url(path)
            urls.append(url)

        return urls

    def _process_url(self, path: str) -> str:
        url = self.url.lower()

        if url.endswith("/"):
            url = url[:-1]

        scheme, extra = "", ""
        for _p in ["http://", "https://"]:
            if url.startswith(_p):
                scheme = _p
                url = url.replace(_p, "")
                break
        else:
            raise ValueError("URL must start with an scheme, http:// or https://.")

        if url.startswith("www."):
            extra = "www."
            url = url.replace("www.", "")

        if "[url]" in path:
            res = f"{scheme}{extra}{path.replace('[url]', url)}"
        else:
            new_path = path[1:] if path.startswith("/") else path
            res = f"{scheme}{extra}{url}/{new_path}"

        return res
