import httpx

from .utils import UserAgent


class Client:

    RETRIES = 0
    HEADERS = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Sec-Fetch-Dest": "document",
        "Sec-GPC": "1",
    }

    def __init__(
        self,
        useragents_path: str,
        retries: int = RETRIES,
        random_useragent: bool = True,
    ) -> None:
        self.transport = httpx.AsyncHTTPTransport(retries=retries)
        self.client = httpx.AsyncClient(transport=self.transport)
        self.uas = UserAgent(useragents_path)
        self.random_useragent = random_useragent

    async def request(self, method: str, url: str, *args, **kwargs) -> httpx.Response:
        if self.random_useragent:
            if not "headers" in kwargs:
                kwargs["headers"] = self.HEADERS.copy()

            kwargs["headers"]["User-Agent"] = self.uas._random

        return await self.client.request(method=method, url=url, *args, **kwargs)
