import re
from dataclasses import dataclass


@dataclass(slots=True)
class Proxy:
    scheme: str
    host: str
    port: int
    username: str | None
    password: str | None

    def __str__(self) -> str:
        auth = ""
        if self.username:
            auth = self.username
            if self.password:
                auth += f":{self.password}"

            auth += "@"

        return f"{self.scheme}{auth}{self.host}:{self.port}"

    @property
    def url(self) -> str:
        return self.__str__()


def _parse_from_url(url: str) -> Proxy | bool:
    pattern = re.compile(
        r"^(?P<scheme>(https?|socks4|socks5):\/\/)"
        r"(?:(?P<username>[^:@\/\s]+)"
        r"(?::(?P<password>[^@\/\s]*))?@)?"
        r"(?P<host>\[[0-9A-Fa-f:.]+\]|[^:\/\s]+)"
        r"(?::(?P<port>(?:6553[0-5]|655[0-2]\d|"
        r"65[0-4]\d{2}|6[0-4]\d{3}|[1-5]\d{4}|\d{1,4})))?"
        r"\/?$"
    )
    match = pattern.match(url)
    if not match:
        return False

    seg = match.groupdict()  # type: ignore
    return Proxy(**seg)  # type: ignore
