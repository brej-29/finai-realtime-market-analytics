from __future__ import annotations

# Re-export commonly used schema modules for convenience.
from .alerts import AlertCreate, AlertRead, AlertEvaluationResult, AlertEventRead  # noqa: F401
from .analytics import (  # noqa: F401
    PortfolioAnalyticsResponse,
    BenchmarkAnalyticsResponse,
    ReturnPoint,
)
from .common import (  # noqa: F401
    AssetType,
    AlertDirection,
    Quote,
    HistoricalBar,
    QuotesResponse,
    HistoryResponse,
    HealthResponse,
)
from .news import NewsArticle, NewsResponse, SentimentScore  # noqa: F401
from .portfolio import (  # noqa: F401
    HoldingCreate,
    HoldingRead,
    PortfolioSummary,
    PortfolioSummaryByType,
)
from .watchlists import (  # noqa: F401
    WatchlistCreate,
    WatchlistItemCreate,
    WatchlistItemRead,
    WatchlistRead,
    WatchlistItemDeleteResult,
)