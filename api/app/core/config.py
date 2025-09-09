from pydantic_settings import BaseSettings
from typing import List, Optional
import os

class Settings(BaseSettings):
    POSTGRES_URL: str = "postgresql+psycopg://user:pass@db:5432/signals"
    REDIS_URL: str = "redis://redis:6379/0"
    SLACK_WEBHOOK: Optional[str] = None
    FINBERT_MODEL: str = "ProsusAI/finbert"
    EMBED_MODEL: str = "sentence-transformers/all-mpnet-base-v2"
    NEWS_FEEDS: str = "https://feeds.a.dj.com/rss/RSSMarketsMain.xml,https://www.nasdaq.com/feed/rssoutbound"
    API_PORT: int = 8000
    WEB_PORT: int = 3000
    API_BASE_URL: str = "http://api:8000"
    WEB_PUBLIC_API: str = "http://localhost:8000"
    SESSION_EXPIRE_SECONDS: int = 86400
    
    # Confidence weights
    # Should have a interface to adjust these dynamically in the future
    W_SRC: float = 0.35
    W_NOVEL: float = 0.25
    W_EVT: float = 0.25
    W_BUZZ: float = 0.15
    K_CONS: float = 0.1
    K_UNC: float = 0.15
    TAU: float = 86400.0
    
    # Thresholds
    # Should have a interface to adjust these dynamically in the future
    MIN_CONFIDENCE_DEFAULT: float = 0.6
    HIGH_PRIORITY_SOURCE_WEIGHT: float = 0.8
    HIGH_NOVELTY_THRESHOLD: float = 0.7
    
    @property
    def news_feeds_list(self) -> List[str]:
        return [f.strip() for f in self.NEWS_FEEDS.split(",")]
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()