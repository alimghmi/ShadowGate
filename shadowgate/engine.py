import asyncio
from collections import Counter
from typing import List
from uuid import uuid4

from .client import Client
from .utils import URLBuilder


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
        sempahore_count: int = SEMAPHORE_COUNT,
        follow_redirects: bool = FOLLOW_REDIRECTS,
    ) -> None:
        self.on = True
        self.c = Client(
            useragents_path=useragents_path,
            retries=retries,
            random_useragent=random_useragent,
            follow_redirects=follow_redirects,
        )
        self.url = url
        self.tasks = []
        self.found_urls = []
        self.semaphore = asyncio.Semaphore(sempahore_count)
        self.built_urls = URLBuilder(url, wordslist_path).compile()[:100]
        self.timeout = timeout
        self.status_codes = status_codes

    async def run(self) -> List:
        print("Starting...")
        host_nf_sc = await self._get_not_found_status_code()
        if host_nf_sc in self.status_codes:
            print(
                f"Found a not found error as interesting status codes, dropping {host_nf_sc}"
            )
            self.status_codes.remove(host_nf_sc)

        try:
            res = await self._worker_manager()
        finally:
            await self.c.client.aclose()
            self.on = False

        return res

    def stop(self) -> None:
        for task in self.tasks:
            task.cancel()

    async def _worker_manager(self) -> List:
        async with asyncio.TaskGroup() as tg:
            self.tasks = [tg.create_task(self._worker(url)) for url in self.built_urls]

        return list(zip(self.built_urls, [task.result() for task in self.tasks]))

    async def _worker(self, url: str):
        async with self.semaphore:
            try:
                result = await self.c.request(
                    "GET", url, follow_redirects=True, timeout=self.timeout
                )
                if result.status_code in self.status_codes:
                    print(url, "FOUND")
                    self.found_urls.append(url)

                return result
            except Exception as e:
                return {"error": type(e).__name__, "details": e}

    async def _get_not_found_status_code(self) -> int:
        built_urls = URLBuilder(
            self.url, [f"[url]/{uuid4().hex}/{uuid4().hex}" for _ in range(5)]
        ).compile()
        tasks = [asyncio.create_task(self.c.request("GET", url)) for url in built_urls]
        status_codes = [resp.status_code for resp in await asyncio.gather(*tasks)]
        sc_counts = Counter(status_codes)
        return sc_counts.most_common(1)[0][0]
