import httpx

from src.config import settings
from src.data_sources.base import DataSource, IdeologicalLean, SearchResult
from src.utils.logger import logger


class NewsAPISource(DataSource):
    """newsapi.org source for conservative news outlets"""

    def __init__(
        self,
        api_key: str | None = None,
        sources: str = "fox-news,breitbart-news,the-wall-street-journal,national-review,the-washington-times",
    ):
        super().__init__()
        self._api_key = api_key or settings.newsapi_key
        self._base_url = "https://newsapi.org/v2/everything"
        self._sources = sources

    @property
    def source_name(self) -> str:
        return "NewsAPI (Conservative)"

    @property
    def ideological_lean(self) -> IdeologicalLean:
        return IdeologicalLean.RIGHT

    async def search(self, query: str, max_results: int = 5) -> list[SearchResult]:
        async with self._rate_limiter:
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.get(
                        self._base_url,
                        headers={"X-Api-Key": self._api_key},
                        params={
                            "q": query,
                            "sources": self._sources,
                            "sortBy": "relevancy",
                            "pageSize": max_results,
                            "language": "en",
                        },
                    )
                    response.raise_for_status()
                    data = response.json()

                    if data.get("status") != "ok":
                        logger.error(f"newsapi error: {data.get('message')}")
                        return []

                    results = []
                    for article in data.get("articles", [])[:max_results]:
                        snippet = (
                            article.get("description")
                            or article.get("content", "")[:200]
                            or article.get("title", "")
                        )

                        results.append(
                            SearchResult(
                                title=article.get("title", ""),
                                url=article.get("url", ""),
                                snippet=snippet,
                                published_date=article.get("publishedAt"),
                                source_name=article.get("source", {}).get(
                                    "name", self.source_name
                                ),
                                ideological_lean=self.ideological_lean,
                            )
                        )

                    return results

            except Exception as e:
                logger.error(f"newsapi error: {e}")
                return []

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    self._base_url,
                    headers={"X-Api-Key": self._api_key},
                    params={"q": "test", "sources": self._sources, "pageSize": 1},
                )
                return response.status_code == 200
        except Exception:
            return False
