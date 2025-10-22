import asyncio
import random
from pathlib import Path
from typing import ClassVar

import httpx
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

from .utils import ProxyHandler, UserAgent


class RetryableStatusError(Exception):
    def __init__(self, status: int) -> None:
        super().__init__(status)
        self.status = status


def _is_retry_status(status: int) -> bool:
    return status in (408, 429) or 500 <= status <= 599


class _RateLimiter:
    def __init__(self, rps: float | None):
        self.rps = rps
        self._lock = asyncio.Lock()
        self._next_time = 0.0
        self._min_interval = (1.0 / rps) if (rps and rps > 0) else 0.0

    async def acquire(self) -> None:
        if not self._min_interval:
            return
        loop = asyncio.get_running_loop()
        async with self._lock:
            now = loop.time()
            if now < self._next_time:
                await asyncio.sleep(self._next_time - now)
                now = loop.time()

            self._next_time = max(now, self._next_time) + self._min_interval


class Client:
    HEADERS: ClassVar = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }

    def __init__(
        self,
        useragents_path: Path,
        timeout: float,
        retries: int,
        random_useragent: bool,
        follow_redirects: bool,
        insecure: bool,
        proxies: Path | list[str] | None = None,
        rps: float | None = None,
    ) -> None:
        if proxies:
            self.proxies = ProxyHandler(proxies)

        self.insecure = insecure
        self._init_clients(timeout, follow_redirects)
        self.uas = UserAgent(useragents_path)
        self.random_useragent = random_useragent
        self._app_retries = max(0, int(retries))
        self._limiter = _RateLimiter(rps)

    async def request(self, method: str, url: str, **kwargs) -> httpx.Response:
        if "headers" not in kwargs:
            kwargs["headers"] = self.HEADERS.copy()

        if self.random_useragent:
            try:
                kwargs["headers"]["User-Agent"] = self.uas._random
            except TypeError as e:
                raise ValueError("headers must be passed as a dict()") from e

        client = self._get_client()
        async for attempt in AsyncRetrying(
            retry=retry_if_exception_type(
                (
                    httpx.ConnectError,
                    httpx.ReadTimeout,
                    httpx.RemoteProtocolError,
                    httpx.WriteError,
                    RetryableStatusError,
                )
            ),
            stop=stop_after_attempt(self._app_retries + 1),
            wait=wait_exponential_jitter(initial=0.25, max=4.0),
            reraise=True,
        ):
            with attempt:
                await self._limiter.acquire()
                resp = await client.request(method=method, url=url, **kwargs)
                if _is_retry_status(resp.status_code):
                    await resp.aread()
                    await resp.aclose()
                    raise RetryableStatusError(resp.status_code)

        return resp

    def is_proxy_available(self) -> bool:
        return hasattr(self, "proxies") and self.proxies.is_available

    def _init_clients(self, timeout: float, follow_redirects: bool):
        if hasattr(self, "proxies") and self.proxies.is_available:
            self.clients = [
                httpx.AsyncClient(
                    proxy=proxy.url,
                    http2=True,
                    follow_redirects=follow_redirects,
                    timeout=timeout,
                    verify=(not self.insecure),
                )
                for proxy in self.proxies.proxies
            ]
        else:
            self.clients = [
                httpx.AsyncClient(
                    http2=True,
                    follow_redirects=follow_redirects,
                    timeout=timeout,
                    verify=(not self.insecure),
                )
            ]

    def _get_client(self) -> httpx.AsyncClient:
        return random.choice(self.clients)

    async def close(self) -> None:
        for client in self.clients:
            await client.aclose()
