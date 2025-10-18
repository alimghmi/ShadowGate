import asyncio
import time
from collections import Counter
from typing import List
from uuid import uuid4

import httpx

from .client import Client
from .logging_setup import get_logger
from .result import ProbeResult
from .utils import URLBuilder

log = get_logger(__name__)


class Engine:

    SEMAPHORE_COUNT = 2
    TIMEOUT = 3
    RETRIES = 1
    WORDSLIST_PATH = "data/wordslist.json"
    USERAGENTS_PATH = "data/user_agents.json"
    STATUS_CODES = [200, 301, 302, 401, 403, 405]
    RANDOM_USERAGENTS = True
    FOLLOW_REDIRECTS = False

    def __init__(
        self,
        url: str,
        wordslist_path: str = WORDSLIST_PATH,
        useragents_path: str = USERAGENTS_PATH,
        timeout: int = TIMEOUT,
        status_codes: List = STATUS_CODES,
        random_useragent: bool = RANDOM_USERAGENTS,
        retries: int = RETRIES,
        semaphore_count: int = SEMAPHORE_COUNT,
        follow_redirects: bool = FOLLOW_REDIRECTS,
    ) -> None:
        log.debug(
            "Engine.__init__ starting",
            extra={
                "url": url,
                "wordslist_path": wordslist_path,
                "useragents_path": useragents_path,
                "timeout": timeout,
                "status_codes": status_codes,
                "random_useragent": random_useragent,
                "retries": retries,
                "semaphore_count": semaphore_count,
                "follow_redirects": follow_redirects,
            },
        )
        self.on = True
        self.url = url
        self.tasks = []
        self.found_urls = []
        self.timeout = timeout
        self.semaphore = asyncio.Semaphore(semaphore_count)
        self.c = Client(
            useragents_path=useragents_path,
            timeout=self.timeout,
            retries=retries,
            random_useragent=random_useragent,
            follow_redirects=follow_redirects,
        )
        self.built_urls = URLBuilder(url, wordslist_path).compile()
        self.status_codes = status_codes
        log.info(
            "Engine initialized",
            extra={"total_built_urls": len(self.built_urls), "timeout": self.timeout},
        )

    async def run(self) -> List:
        log.info("Scan starting", extra={"target": self.url})
        host_nf_sc = await self._get_not_found_status_code()
        if host_nf_sc:
            log.debug(
                "Detected host-specific not-found status code",
                extra={"status_code": host_nf_sc},
            )
            if host_nf_sc in self.status_codes:
                log.info(
                    "Dropping not-found code from interesting status codes",
                    extra={"dropped": host_nf_sc},
                )
                self.status_codes.remove(host_nf_sc)

        try:
            res = await self._worker_manager()
            log.info(
                "Worker manager completed",
                extra={
                    "total_urls": len(self.built_urls),
                    "found_count": len(self.found_urls),
                },
            )
        finally:
            await self.c.client.aclose()
            self.on = False
            log.info("HTTP client closed and engine stopped")

        return res

    def stop(self) -> None:
        log.warning(
            "Engine.stop called; cancelling tasks", extra={"tasks": len(self.tasks)}
        )
        for task in self.tasks:
            task.cancel()

    async def _worker_manager(self) -> List:
        log.debug(
            "Creating worker tasks",
            extra={"count": len(self.built_urls), "semaphore": self.semaphore._value},
        )
        async with asyncio.TaskGroup() as tg:
            self.tasks = [tg.create_task(self._worker(url)) for url in self.built_urls]

        results = list(zip(self.built_urls, [task.result() for task in self.tasks]))
        log.debug(
            "Collected worker results",
            extra={"results_count": len(results), "found_count": len(self.found_urls)},
        )
        return results

    async def _worker(self, url: str) -> ProbeResult:
        log.debug("Worker acquiring semaphore", extra={"url": url})
        async with self.semaphore:
            try:
                t1 = time.perf_counter()
                result = await self.c.request("GET", url)
                if result.status_code in self.status_codes:
                    self.found_urls.append(url)
                    log.info(
                        "Interesting URL found",
                        extra={"url": url, "status": result.status_code},
                    )
                t2 = time.perf_counter()
                return ProbeResult(
                    url=url,
                    status=result.status_code,
                    elapsed=(t2 - t1),
                    ok=(result.status_code in self.status_codes),
                )
            except asyncio.CancelledError:
                log.debug("Worker cancelled", extra={"url": url})
                raise
            except (
                httpx.ConnectError,
                httpx.ReadTimeout,
                httpx.RemoteProtocolError,
                httpx.HTTPStatusError,
            ) as e:
                log.warning(
                    "Network error", extra={"url": url, "error": type(e).__name__}
                )
                return ProbeResult(
                    url=url, status=None, ok=False, error=type(e).__name__
                )
            except Exception as e:
                log.error(
                    "Unexpected error",
                    extra={"url": url, "error": type(e).__name__},
                    exc_info=True,
                )
                return ProbeResult(
                    url=url, status=None, ok=False, error="UnexpectedError"
                )

    async def _get_not_found_status_code(self) -> int | None:
        log.debug("Calculating host not-found status code", extra={"host": self.url})
        built_urls = URLBuilder(
            self.url, [f"[url]/{uuid4().hex}/{uuid4().hex}" for _ in range(5)]
        ).compile()
        tasks = [asyncio.create_task(self.c.request("GET", url)) for url in built_urls]
        status_codes = [resp.status_code for resp in await asyncio.gather(*tasks)]
        if not status_codes:
            return None

        sc_counts = Counter(status_codes)
        top = sc_counts.most_common(1)[0][0] or None
        log.info(
            "Computed not-found status code",
            extra={"most_common": top, "distribution": dict(sc_counts)},
        )
        return top
