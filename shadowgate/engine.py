import asyncio
import time
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4

import httpx

from .client import Client
from .entities.result import ProbeResult
from .logging_setup import get_logger
from .utils import URLBuilder

log = get_logger(__name__)


class Engine:
    def __init__(
        self,
        url: str,
        status_codes: list,
        random_useragent: bool,
        follow_redirects: bool,
        timeout: int,
        retries: int,
        rps: float,
        semaphore_count: int,
        insecure: bool,
        wordslist_path: Path,
        useragents_path: Path,
        proxies: Path | list[str] | None = None,
    ) -> None:
        log.debug(
            "Engine.__init__ starting",
            extra={
                "url": url,
                "wordslist_path": wordslist_path,
                "useragents_path": useragents_path,
                "proxies": proxies,
                "timeout": timeout,
                "rps": rps,
                "status_codes": status_codes,
                "random_useragent": random_useragent,
                "retries": retries,
                "semaphore_count": semaphore_count,
                "follow_redirects": follow_redirects,
                "insecure": insecure,
            },
        )
        self.on = True
        self.url = url
        self.tasks = []
        self.found_urls = []
        self.timeout = timeout
        self.follow_redirects = follow_redirects
        self.semaphore = asyncio.Semaphore(semaphore_count)
        self.c = Client(
            useragents_path=useragents_path,
            proxies=proxies,
            insecure=insecure,
            timeout=self.timeout,
            rps=rps,
            retries=retries,
            random_useragent=random_useragent,
            follow_redirects=self.follow_redirects,
        )
        self.built_urls = URLBuilder(url, wordslist_path).compile()
        self.status_codes = status_codes
        log.info(
            "Engine initialized",
            extra={"total_built_urls": len(self.built_urls), "timeout": self.timeout},
        )

    async def run(self) -> list:
        log.info("Scan starting", extra={"target": self.url})
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
            await self.c.close()
            log.info("HTTP client closed and engine stopped")

        await asyncio.sleep(1)  # For cli module to read final updates before exiting
        self.on = False
        return res

    def stop(self) -> None:
        log.warning("Engine.stop called; cancelling tasks", extra={"tasks": len(self.tasks)})
        for task in self.tasks:
            task.cancel()

    async def check_target(self) -> bool:
        log.info("Performing pre-flight check", extra={"target": self.url})
        parsed = urlparse(self.url)
        if parsed.scheme not in {"http", "https"}:
            log.error("Invalid URL scheme", extra={"scheme": parsed.scheme})
            return False

        try:
            response = await self.c.request(
                "GET",
                self.url.rstrip("/"),
                timeout=self.timeout,
            )

            if response.status_code >= 400 and response.status_code not in (401, 403):
                log.warning(
                    "Target appears unavailable",
                    extra={"status": response.status_code},
                )
                return False

            log.info(
                "Target is reachable",
                extra={"status": response.status_code, "url": str(response.url)},
            )
            return True

        except Exception as e:
            log.error(
                "Unexpected error during pre-flight check",
                extra={"error": type(e).__name__, "details": str(e)},
                exc_info=True,
            )
            return False

    async def _worker_manager(self) -> list:
        log.debug(
            "Creating worker tasks",
            extra={"count": len(self.built_urls), "semaphore": self.semaphore._value},
        )
        results: list[tuple[str, ProbeResult]] = []

        async with asyncio.TaskGroup() as tg:
            self.tasks = [tg.create_task(self._worker(url)) for url in self.built_urls]

        for url, task in zip(self.built_urls, self.tasks, strict=False):
            if task.cancelled():
                pr = ProbeResult(url=url, status=None, ok=False, error="Cancelled")
            elif task.exception() is not None:
                exc = task.exception()
                log.error(
                    "Worker raised unexpectedly",
                    extra={"url": url, "error": type(exc).__name__},
                )
                pr = ProbeResult(url=url, status=None, ok=False, error=type(exc).__name__)
            else:
                pr = task.result()

            results.append((url, pr))

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
                if result and result.status_code in self.status_codes:
                    self.found_urls.append(url)
                    log.debug(
                        "Interesting URL found",
                        extra={"url": url, "status": result.status_code},
                    )

                t2 = time.perf_counter()
                return ProbeResult(
                    url=url,
                    status=(
                        result.status_code if result and hasattr(result, "status_code") else None
                    ),
                    elapsed=(t2 - t1),
                    ok=(
                        result.status_code in self.status_codes
                        if result and hasattr(result, "status_code")
                        else False
                    ),
                )
            except asyncio.CancelledError:
                log.debug("Worker cancelled", extra={"url": url})
                raise
            except (
                httpx.ConnectError,
                httpx.ReadTimeout,
                httpx.RemoteProtocolError,
                httpx.HTTPStatusError,
                httpx.ConnectTimeout,
            ) as e:
                log.warning("Network error", extra={"url": url, "error": type(e).__name__})
                return ProbeResult(url=url, status=None, ok=False, error=type(e).__name__)
            except Exception as e:
                log.error(
                    "Unexpected error",
                    extra={"url": url, "error": type(e).__name__},
                    exc_info=True,
                )
                return ProbeResult(url=url, status=None, ok=False, error="UnexpectedError")

    async def _make_random_request(self, n: int = 5) -> list:
        built_urls = URLBuilder(
            self.url, [f"[url]/{uuid4().hex}/{uuid4().hex}" for _ in range(n)]
        ).compile()
        log.debug(f"{built_urls}")
        tasks = [
            asyncio.create_task(self.c.request("GET", url, follow_redirects=self.follow_redirects))
            for url in built_urls
        ]
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        return responses

    async def get_not_found_status_code(self) -> int | None:
        log.debug("Calculating host not-found status code", extra={"host": self.url})
        responses = await self._make_random_request()
        status_codes = [
            getattr(r, "status_code", None) for r in responses if not isinstance(r, Exception)
        ]
        if not status_codes:
            return

        sc_counts = Counter(status_codes)
        top = sc_counts.most_common(1)[0][0] or None
        log.info(
            "Computed not-found status code",
            extra={"most_common": top, "distribution": dict(sc_counts)},
        )
        return top
