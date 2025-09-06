from typing import Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class RawDoc:
    url: str
    title: str
    published: Optional[str]
    source: str
    content: Optional[str] = None
    html: Optional[str] = None
    meta: Dict[str, Any] = None

@dataclass
class NormalizedDoc:
    source: str
    url: str
    title: str
    published_at: Optional[str]
    fetched_at: Optional[str]
    raw_text: str
    html_snapshot_path: Optional[str]
    content_hash: str
    lang: Optional[str]
    meta: Dict[str, Any]

class BaseAdapter:
    def __init__(self, config: Dict[str, Any]):
        self.config = config

    async def fetch(self) -> Optional[RawDoc]:
        raise NotImplementedError()

    async def normalize(self, raw: RawDoc) -> NormalizedDoc:
        raise NotImplementedError()
