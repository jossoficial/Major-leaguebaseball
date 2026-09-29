import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable

import pandas as pd

from src.utils.constants import CACHE_DIR, SETTINGS
from src.utils.logger import get_logger

logger = get_logger(__name__)


class CacheManager:
    """Cache unificado por categoria con TTL configurable.

    - DataFrames  -> .parquet + .meta (timestamp)
    - JSON/dicts  -> .json + .meta
    """

    def __init__(self, category: str, ttl_hours: float | None = None):
        self.category = category
        default = SETTINGS["cache"]["ttl_hours"].get(category, 24)
        self.ttl = timedelta(hours=ttl_hours if ttl_hours is not None else default)
        self.dir = Path(CACHE_DIR) / category
        self.dir.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str, ext: str) -> Path:
        h = hashlib.md5(key.encode()).hexdigest()
        return self.dir / f"{h}.{ext}"

    def _fresh(self, path: Path) -> bool:
        meta = path.with_suffix(".meta")
        if not path.exists() or not meta.exists():
            return False
        created = json.loads(meta.read_text()).get("created", 0)
        return (datetime.now().timestamp() - created) <= self.ttl.total_seconds()

    def _stamp(self, path: Path) -> None:
        path.with_suffix(".meta").write_text(
            json.dumps({"created": datetime.now().timestamp()}))

    # ---------------- DataFrames ----------------
    def get(self, key: str) -> pd.DataFrame | None:
        path = self._path(key, "parquet")
        if not self._fresh(path):
            return None
        logger.debug("Cache HIT [%s] %s", self.category, key)
        return pd.read_parquet(path)

    def set(self, key: str, df: pd.DataFrame) -> None:
        path = self._path(key, "parquet")
        df.to_parquet(path, index=False)
        self._stamp(path)

    def get_or_fetch(self, key: str, fetch_fn: Callable[[], pd.DataFrame]) -> pd.DataFrame:
        cached = self.get(key)
        if cached is not None:
            return cached
        df = fetch_fn()
        self.set(key, df)
        return df

    # ---------------- JSON ----------------
    def get_json(self, key: str) -> dict | list | None:
        path = self._path(key, "json")
        if not self._fresh(path):
            return None
        return json.loads(path.read_text())

    def set_json(self, key: str, obj: dict | list) -> None:
        path = self._path(key, "json")
        path.write_text(json.dumps(obj))
        self._stamp(path)

    # ---------------- utilidades ----------------
    def clear_expired(self) -> int:
        removed = 0
        for meta in self.dir.glob("*.meta"):
            data = meta.with_suffix("")
            created = json.loads(meta.read_text()).get("created", 0)
            if datetime.now().timestamp() - created > self.ttl.total_seconds():
                for p in (meta, data):
                    if p.exists():
                        p.unlink()
                        removed += 1
        return removed
