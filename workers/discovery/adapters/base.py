"""Source adapter protocol and base types."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterator, Optional, Protocol


@dataclass
class SearchQuery:
    """Normalized discovery query."""

    text: str
    location: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    radius_m: int = 25000
    max_results: int = 20
    industry_keywords: list = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RawRecord:
    """Immutable source observation prior to normalization."""

    source: str
    external_id: str
    payload: Dict[str, Any]


@dataclass
class SourceCapabilities:
    """What a source adapter can do."""

    search: bool = True
    fetch: bool = False
    rate_limit_per_minute: int = 30


class SourceAdapter(Protocol):
    """Common interface for discovery adapters."""

    def search(self, query: SearchQuery) -> Iterator[RawRecord]:
        ...

    def fetch(self, external_id: str) -> RawRecord:
        ...

    def capabilities(self) -> SourceCapabilities:
        ...
