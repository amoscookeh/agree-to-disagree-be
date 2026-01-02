import httpx

from src.config import settings
from src.data_sources.base import DataSource, IdeologicalLean, SearchResult
from src.utils.logger import logger


class GuardianSource(DataSource):
    def __init__(self, api_key: str | None = None):
        super().__init__()
        self._api_key = api_key or settings.guardian_api_key
        self._base_url = "https://content.guardianapis.com/search"

    @property
    def source_name(self) -> str:
        return "The Guardian"

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
                            "page-size": max_results,
                            "show-fields": "trailText,bodyText",
                            "order-by": "relevance",
                        },
                    )
                    response.raise_for_status()
                    data = response.json()

                    results = []
                    for item in data.get("response", {}).get("results", []):
                        snippet = (
                            item.get("fields", {}).get("trailText")
                            or item.get("fields", {}).get("bodyText", "")[:200]
                        )

                        results.append(
                            SearchResult(
                                title=item.get("webTitle", ""),
                                url=item.get("webUrl", ""),
                                snippet=snippet,
                                published_date=item.get("webPublicationDate"),
                                source_name=self.source_name,
                                ideological_lean=self.ideological_lean,
                            )
                        )

                    return results

            except Exception as e:
                logger.error(f"guardian api error: {e}")
                return []

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    self._base_url, params={"api-key": self._api_key, "page-size": 1}
                )
                return response.status_code == 200
        except Exception:
            return False
