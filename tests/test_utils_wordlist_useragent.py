import json
from pathlib import Path

from shadowgate.utils.useragent_helper import UserAgent
from shadowgate.utils.wordlist_helper import URLBuilder, WordsListLoader


def test_wordslist_loader_custom_file(tmp_path: Path):
    payload = {"paths": ["/admin", "/login"]}
    f = tmp_path / "words.json"
    f.write_text(json.dumps(payload["paths"]))
    wl = WordsListLoader(wordslists_path=f)
    assert wl.load() == payload["paths"]


def test_useragent_loader_custom_file_and_random(tmp_path: Path):
    uas = ["UA-1", "UA-2"]
    f = tmp_path / "uas.json"
    f.write_text(json.dumps(uas))
    ua = UserAgent(useragents_path=f)
    assert set(ua._load_uas()) == set(uas)
    assert ua._random in uas


def test_urlbuilder_builds_variants():
    base = "https://example.com"
    urls = URLBuilder(base, ["/admin", "[url]/login", "https://other/path"]).compile()
    assert base + "/admin" in urls
    assert "https://example.com/login" in urls
