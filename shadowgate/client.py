import httpx

from .utils import UserAgent


class Client:

    RETRIES = 0
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }

    def __init__(
        self,
        useragents_path: str,
        retries: int = RETRIES,
        random_useragent: bool = True,
        follow_redirects: bool = True,
    ) -> None:
        self.transport = httpx.AsyncHTTPTransport(retries=retries)
        self.client = httpx.AsyncClient(
            transport=self.transport, http2=True, follow_redirects=follow_redirects
        )
        self.uas = UserAgent(useragents_path)
        self.random_useragent = random_useragent

    async def request(self, method: str, url: str, *args, **kwargs) -> httpx.Response:
        if not "headers" in kwargs:
            kwargs["headers"] = self.HEADERS.copy()

        if self.random_useragent:
            try:
                kwargs["headers"]["User-Agent"] = self.uas._random
            except TypeError:
                raise ValueError("headers must be passed as a dict()")

        return await self.client.request(method=method, url=url, *args, **kwargs)
