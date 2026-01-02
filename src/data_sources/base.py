from abc import ABC, abstractmethod
from asyncio import Semaphore
from enum import Enum

from pydantic import BaseModel


class IdeologicalLean(str, Enum):
    LEFT = "left"
    RIGHT = "right"
    NEUTRAL = "neutral"


class SearchResult(BaseModel):
    title: str
    url: str
    snippet: str
    published_date: str | None = None
    source_name: str
    ideological_lean: IdeologicalLean


class DataSource(ABC):
    def __init__(self, max_concurrent: int = 5):
        self._rate_limiter = Semaphore(max_concurrent)

    @abstractmethod
    async def search(self, query: str, max_results: int = 5) -> list[SearchResult]:
        pass

    @property
    @abstractmethod
    def source_name(self) -> str:
        pass

    @property
    @abstractmethod
    def ideological_lean(self) -> IdeologicalLean:
        pass

    @property
    def enabled(self) -> bool:
        return True

    async def health_check(self) -> bool:
        return True
