import json
import random
from pathlib import Path
from typing import List

from ..engine import Engine
from .misc import _read_file


class UserAgent:

    def __init__(self, useragents_path: Path) -> None:
        self.useragents_path = useragents_path
        self.uas = self._load_uas()

    @property
    def _random(self) -> str:
        return random.choice(self.uas)

    def _load_uas(self) -> List[str]:
        if self.useragents_path == Engine.USERAGENTS_PATH:
            return json.loads(_read_file(self.useragents_path))
        else:
            return json.load(open(self.useragents_path, "r"))
