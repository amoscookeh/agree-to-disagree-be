from src.data_sources.base import DataSource, IdeologicalLean, SearchResult
from src.data_sources.registry import DataSourceRegistry


def get_default_registry() -> DataSourceRegistry:
    """create registry with all configured data sources"""
    from src.config import settings
    from src.data_sources.left_leaning import GuardianSource, NYTSource
    from src.data_sources.right_leaning import (
        BreitbartRSSSource,
        DailyWireRSSSource,
        NewsAPISource,
        NYPostRSSSource,
    )

    registry = DataSourceRegistry()

    registry.register_left(GuardianSource())
    registry.register_left(NYTSource())

    registry.register_right(NYPostRSSSource())
    registry.register_right(BreitbartRSSSource())
    registry.register_right(DailyWireRSSSource())
    
    if settings.newsapi_key:
        registry.register_right(NewsAPISource())

    return registry


def search_result_to_dict(result: SearchResult) -> dict:
    """convert SearchResult to dict for state/serialization"""
    return {
        "title": result.title,
        "url": result.url,
        "snippet": result.snippet,
        "published_date": result.published_date,
        "source_name": result.source_name,
        "ideological_lean": result.ideological_lean.value,
    }


__all__ = [
    "DataSource",
    "IdeologicalLean",
    "SearchResult",
    "DataSourceRegistry",
    "get_default_registry",
    "search_result_to_dict",
]
