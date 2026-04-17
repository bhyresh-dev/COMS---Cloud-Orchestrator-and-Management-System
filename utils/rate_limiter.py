"""
COMS — In-memory token-bucket rate limiter.

Usage:
    from utils.rate_limiter import check_rate_limit

    allowed, wait = check_rate_limit(user_id="uid_abc", action="nlp_request", limit=20, window=60)
    if not allowed:
        raise HTTPException(status_code=429, detail=f"Rate limit exceeded. Retry after {wait}s.")
"""
import time
import threading
from collections import defaultdict, deque

_lock = threading.Lock()
# { (user_id, action) : deque of timestamps }
_buckets: dict = defaultdict(deque)


def check_rate_limit(user_id: str, action: str,
                     limit: int = 20, window: int = 60) -> tuple[bool, int]:
    """
    Returns (allowed: bool, retry_after_seconds: int).
    limit  = max calls allowed in the window
    window = rolling window in seconds
    """
    key = (user_id, action)
    now = time.time()

    with _lock:
        bucket = _buckets[key]

        # Remove timestamps outside the window
        while bucket and bucket[0] < now - window:
            bucket.popleft()

        if len(bucket) >= limit:
            oldest = bucket[0]
            retry_after = int(window - (now - oldest)) + 1
            return False, retry_after

        bucket.append(now)
        return True, 0
