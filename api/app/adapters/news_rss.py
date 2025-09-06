from typing import List, Dict, Any
import feedparser
import httpx
from .base import RawDoc
from datetime import datetime
import structlog

logger = structlog.get_logger()

class NewsRSSAdapter:
    def __init__(self, config: Dict[str, Any]):
        self.config = config

    async def fetch(self) -> List[RawDoc]:
        urls = self.config.get('urls') or []
        results = []

        for url in urls:
            try:
                logger.info('fetching_feed', feed=url)
                feed = feedparser.parse(url)
                for entry in feed.entries[:50]:
                    published = None
                    if entry.get('published_parsed'):
                        published = datetime.fromtimestamp(
                            int(datetime(*entry.published_parsed[:6]).timestamp())
                        ).isoformat()

                    raw = RawDoc(
                        url=entry.get('link', ''),
                        title=entry.get('title', '') or '',
                        published=published,
                        source=self.config.get('source_name') or url,
                        content=None
                    )
                    results.append(raw)
            except Exception as e:
                logger.error('feed_error', feed=url, error=str(e))
                continue

        return results
