import asyncio

from src.data_sources.base import DataSource, SearchResult
from src.utils.logger import logger


class DataSourceRegistry:
    def __init__(self) -> None:
        self._left_sources: list[DataSource] = []
        self._right_sources: list[DataSource] = []
        self._academic_sources: list[DataSource] = []

    def register_left(self, source: DataSource) -> None:
        self._left_sources.append(source)

    def register_right(self, source: DataSource) -> None:
        self._right_sources.append(source)

    def register_academic(self, source: DataSource) -> None:
        self._academic_sources.append(source)

    async def search_left(self, query: str, max_results: int = 5) -> list[SearchResult]:
        return await self._search_sources(self._left_sources, query, max_results)

    async def search_right(
        self, query: str, max_results: int = 5
    ) -> list[SearchResult]:
        return await self._search_sources(self._right_sources, query, max_results)

    async def search_academic(
        self, query: str, max_results: int = 5
    ) -> list[SearchResult]:
        return await self._search_sources(self._academic_sources, query, max_results)

    async def search_all(self, query: str, max_results: int = 5) -> dict:
        left_task = self.search_left(query, max_results)
        right_task = self.search_right(query, max_results)
        academic_task = self.search_academic(query, max_results)

        left_results, right_results, academic_results = await asyncio.gather(
            left_task, right_task, academic_task, return_exceptions=True
        )

        return {
            "left": left_results if not isinstance(left_results, Exception) else [],
            "right": right_results if not isinstance(right_results, Exception) else [],
            "academic": (
                academic_results if not isinstance(academic_results, Exception) else []
            ),
        }

    async def _search_sources(
        self, sources: list[DataSource], query: str, max_results: int
    ) -> list[SearchResult]:
        if not sources:
            return []

        tasks = [source.search(query, max_results) for source in sources]
        results_or_errors = await asyncio.gather(*tasks, return_exceptions=True)

        all_results: list[SearchResult] = []
        for i, result in enumerate(results_or_errors):
            if isinstance(result, BaseException):
                logger.warning(f"source {sources[i].source_name} failed: {result}")
                continue
            all_results.extend(result)

        return all_results

    def list_sources(self) -> list[dict]:
        sources = []

        for source in self._left_sources:
            sources.append(
                {
                    "name": source.source_name,
                    "lean": source.ideological_lean.value,
                    "enabled": source.enabled,
                }
            )

        for source in self._right_sources:
            sources.append(
                {
                    "name": source.source_name,
                    "lean": source.ideological_lean.value,
                    "enabled": source.enabled,
                }
            )

        for source in self._academic_sources:
            sources.append(
                {
                    "name": source.source_name,
                    "lean": source.ideological_lean.value,
                    "enabled": source.enabled,
                }
            )

        return sources
