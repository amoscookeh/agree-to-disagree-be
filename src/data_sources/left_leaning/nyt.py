import httpx

from src.config import settings
from src.data_sources.base import DataSource, IdeologicalLean, SearchResult
from src.utils.logger import logger


class NYTSource(DataSource):
    def __init__(self, api_key: str | None = None):
        super().__init__()
        self._api_key = api_key or settings.nyt_api_key
        self._base_url = "https://api.nytimes.com/svc/search/v2/articlesearch.json"

    @property
    def source_name(self) -> str:
        return "The New York Times"

    @property
    def ideological_lean(self) -> IdeologicalLean:
        return IdeologicalLean.LEFT

    async def search(self, query: str, max_results: int = 5) -> list[SearchResult]:
        async with self._rate_limiter:
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.get(
                        self._base_url,
                        params={
                            "q": query,
                            "api-key": self._api_key,
                            "sort": "relevance",
                            "page": 0,
                        },
                    )
                    response.raise_for_status()
                    data = response.json()

                    results = []
                    docs = data.get("response", {}).get("docs", [])

                    for doc in docs[:max_results]:
                        snippet = (
                            doc.get("abstract")
                            or doc.get("lead_paragraph", "")[:200]
                            or doc.get("snippet", "")
                        )

                        results.append(
                            SearchResult(
                                title=doc.get("headline", {}).get("main", ""),
                                url=doc.get("web_url", ""),
                                snippet=snippet,
                                published_date=doc.get("pub_date"),
                                source_name=self.source_name,
                                ideological_lean=self.ideological_lean,
                            )
                        )

                    return results

            except Exception as e:
                logger.error(f"nyt api error: {e}")
                return []

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    self._base_url, params={"api-key": self._api_key, "q": "test"}
                )
                return response.status_code == 200
        except Exception:
            return False
