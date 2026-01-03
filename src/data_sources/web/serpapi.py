import httpx

from src.config import settings
from src.data_sources.base import IdeologicalLean, SearchResult
from src.utils.logger import logger


class SerpAPIClient:
    """google search via SerpAPI for stats and additional sources"""

    def __init__(self):
        self.api_key = settings.serpapi_key
        self.base_url = "https://serpapi.com/search"
        self.enabled = bool(self.api_key)

    async def search(
        self,
        query: str,
        num_results: int = 5,
        search_type: str = "general",
    ) -> list[SearchResult]:
        if not self.enabled:
            logger.debug("serpapi disabled (no api key)")
            return []

        params = {
            "q": query,
            "api_key": self.api_key,
            "num": num_results,
        }

        if search_type == "news":
            params["tbm"] = "nws"
        elif search_type == "scholar":
            params["engine"] = "google_scholar"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(self.base_url, params=params)
                response.raise_for_status()
                data = response.json()

            results = []
            organic_results = data.get("organic_results", [])

            for item in organic_results[:num_results]:
                results.append(
                    SearchResult(
                        title=item.get("title", ""),
                        url=item.get("link", ""),
                        snippet=item.get("snippet", ""),
                        published_date=item.get("date"),
                        source_name="Google Search",
                        ideological_lean=IdeologicalLean.NEUTRAL,
                    )
                )

            logger.info(
                f"serpapi returned {len(results)} results for query: {query[:50]}"
            )
            return results

        except httpx.HTTPStatusError as e:
            logger.error(f"serpapi http error: {e.response.status_code}")
            return []
        except Exception as e:
            logger.error(f"serpapi search failed: {e}")
            return []


serpapi_client = SerpAPIClient()
