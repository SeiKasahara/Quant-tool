import hashlib
from typing import Optional
try:
    from datasketch import MinHash
except Exception:
    MinHash = None

def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode('utf8')).hexdigest()

def is_near_duplicate(text: str, threshold: float = 0.9) -> bool:
    # Placeholder: if datasketch present, implement MinHash Jaccard; else return False
    if MinHash is None:
        return False
    m = MinHash()
    for token in text.split():
        m.update(token.encode('utf8'))
    # In production, compare against sliding window index in Redis/DB
    return False
