import json
import random
from pathlib import Path

from .misc import _read_file


class UserAgent:
    USERAGENTS_PATH = Path("data/user_agents.json")

    def __init__(self, useragents_path: Path) -> None:
        self.useragents_path = useragents_path
        self.uas = self._load_uas()

    @property
    def _random(self) -> str:
        return random.choice(self.uas)

    def _load_uas(self) -> list[str]:
        if self.useragents_path == self.USERAGENTS_PATH:
            return json.loads(_read_file(self.useragents_path))
        else:
            return json.load(open(self.useragents_path))
