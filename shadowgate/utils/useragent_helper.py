import json
import random
from pathlib import Path
from typing import List

from .misc import _read_file


class UserAgent:

    def __init__(self, useragents_path: Path) -> None:
        self.useragents_path = useragents_path
        self.uas = self._load_uas()

    @property
    def _random(self) -> str:
        return random.choice(self.uas)

    def _load_uas(self) -> List[str]:
        return json.loads(_read_file(self.useragents_path))
