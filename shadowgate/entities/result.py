from dataclasses import asdict, dataclass


@dataclass(slots=True)
class ProbeResult:
    url: str
    status: int | None
    ok: bool
    error: str | None = None
    elapsed: float | None = None

    def to_dict(self) -> dict:
        return asdict(self)
