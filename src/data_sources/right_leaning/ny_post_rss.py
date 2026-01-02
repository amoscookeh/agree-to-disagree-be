from datetime import datetime

import feedparser
import httpx

from src.data_sources.base import DataSource, IdeologicalLean, SearchResult
from src.utils.logger import logger


class NYPostRSSSource(DataSource):
    def __init__(self):
        super().__init__()
        self._feed_url = "https://nypost.com/feed/"

    @property
    def source_name(self) -> str:
        return "NY Post"

    @property
    def ideological_lean(self) -> IdeologicalLean:
        return IdeologicalLean.RIGHT

    async def search(self, query: str, max_results: int = 5) -> list[SearchResult]:
        async with self._rate_limiter:
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.get(self._feed_url)
                    response.raise_for_status()
                    feed_content = response.text

                feed = feedparser.parse(feed_content)

                query_lower = query.lower()
                results = []

                for entry in feed.entries:
                    title = entry.get("title", "")
                    summary = entry.get("summary", "")

                    if query_lower in title.lower() or query_lower in summary.lower():
                        published_date = None
                        if (
                            hasattr(entry, "published_parsed")
                            and entry.published_parsed
                        ):
                            try:
                                dt = datetime(*entry.published_parsed[:6])
                                published_date = dt.isoformat()
                            except Exception:
                                pass

                        snippet = summary[:200] if summary else title[:200]

                        results.append(
                            SearchResult(
                                title=title,
                                url=entry.get("link", ""),
                                snippet=snippet,
                                published_date=published_date,
                                source_name=self.source_name,
                                ideological_lean=self.ideological_lean,
                            )
                        )

                        if len(results) >= max_results:
                            break

                return results

            except Exception as e:
                logger.error(f"ny post rss error: {e}")
                return []

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(self._feed_url)
                return response.status_code == 200
        except Exception:
            return False
