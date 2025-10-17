import asyncio
import os
from typing import List

from .client import Client
from .utils import URLCompiler


class Engine:

    SEMAPHORE_COUNT = 2
    TIMEOUT = 3
    RETRIES = 1
    WORDSLIST_PATH = os.path.join(os.getcwd(), ("assets/wordslist.json"))
    USERAGENTS_PATH = os.path.join(os.getcwd(), ("assets/ua.json"))
    STATUS_CODES = [200, 301, 401, 500]
    RANDOM_USERAGENTS = True

    def __init__(
        self,
        url: str,
        wordslist_path: str = WORDSLIST_PATH,
        useragents_path: str = USERAGENTS_PATH,
        timeout: int = TIMEOUT,
        status_codes: List = STATUS_CODES,
        random_ua: bool = RANDOM_USERAGENTS,
        retries: int = RETRIES,
        sempahore_count: int = SEMAPHORE_COUNT,
    ) -> None:
        self.on = True
        self.c = Client(
            useragents_path=useragents_path, retries=retries, random_useragent=random_ua
        )
        self.url = url
        self.tasks = []
        self.found_urls = []
        self.semaphore = asyncio.Semaphore(sempahore_count)
        self.compiled_urls = URLCompiler(url, wordslist_path).compile()[:100]
        self.timeout = timeout
        self.status_codes = status_codes

    async def run(self) -> List:
        print("Starting...")
        res = await self._worker_manager()
        await self.c.client.aclose()
        self.on = False
        return res

    async def _worker_manager(self) -> List:
        async with asyncio.TaskGroup() as tg:
            self.tasks = [
                tg.create_task(self._worker(url)) for url in self.compiled_urls
            ]

        return list(zip(self.compiled_urls, [task.result() for task in self.tasks]))

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
