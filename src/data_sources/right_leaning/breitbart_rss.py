from datetime import datetime
import re

import feedparser
import httpx

from src.data_sources.base import DataSource, IdeologicalLean, SearchResult
from src.utils.logger import logger


def _tokenize(text: str) -> set[str]:
    return set(re.findall(r'\b[a-z]+\b', text.lower()))


def _relevance_score(query: str, title: str, summary: str) -> float:
    query_words = _tokenize(query)
    content_words = _tokenize(f"{title} {summary}")
    
    if not query_words:
        return 0.0
    
    matches = query_words & content_words
    score = len(matches) / len(query_words)
    
    title_words = _tokenize(title)
    title_matches = query_words & title_words
    if title_matches:
        score += 0.3 * (len(title_matches) / len(query_words))
    
    return min(score, 1.0)


class BreitbartRSSSource(DataSource):
    def __init__(self):
        super().__init__()
        self._feed_urls = [
            "https://feeds.feedburner.com/breitbart",
        ]

    @property
    def source_name(self) -> str:
        return "Breitbart"

    @property
    def ideological_lean(self) -> IdeologicalLean:
        return IdeologicalLean.RIGHT

    async def search(self, query: str, max_results: int = 5) -> list[SearchResult]:
        async with self._rate_limiter:
            all_entries = []
            
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    for feed_url in self._feed_urls:
                        try:
                            response = await client.get(feed_url)
                            response.raise_for_status()
                            feed = feedparser.parse(response.text)
                            all_entries.extend(feed.entries)
                        except Exception as e:
                            logger.warning(f"failed to fetch {feed_url}: {e}")
                
                scored_entries = []
                for entry in all_entries:
                    title = entry.get("title", "")
                    summary = entry.get("summary", entry.get("description", ""))
                    score = _relevance_score(query, title, summary)
                    
                    if score > 0.2:
                        scored_entries.append((score, entry))
                
                scored_entries.sort(key=lambda x: x[0], reverse=True)
                
                results = []
                seen_urls = set()
                
                for score, entry in scored_entries[:max_results]:
                    url = entry.get("link", "")
                    if url in seen_urls:
                        continue
                    seen_urls.add(url)
                    
                    title = entry.get("title", "")
                    summary = entry.get("summary", entry.get("description", ""))
                    
                    published_date = None
                    if hasattr(entry, "published_parsed") and entry.published_parsed:
                        try:
                            dt = datetime(*entry.published_parsed[:6])
                            published_date = dt.isoformat()
                        except Exception:
                            pass
                    
                    snippet = summary[:200] if summary else title[:200]
                    snippet = re.sub(r'<[^>]+>', '', snippet)
                    
                    results.append(
                        SearchResult(
                            title=title,
                            url=url,
                            snippet=snippet,
                            published_date=published_date,
                            source_name=self.source_name,
                            ideological_lean=self.ideological_lean,
                        )
                    )
                
                logger.info(f"breitbart rss: found {len(results)} results for '{query}'")
                return results

            except Exception as e:
                logger.error(f"breitbart rss error: {e}")
                return []

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(self._feed_urls[0])
                return response.status_code == 200
        except Exception:
            return False

