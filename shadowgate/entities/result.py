from dataclasses import asdict, dataclass
from typing import Dict, Optional


@dataclass(slots=True)
class ProbeResult:
    url: str
    status: Optional[int]
    ok: bool
    error: Optional[str] = None
    elapsed: Optional[float] = None

    def to_dict(self) -> Dict:
        return asdict(self)
