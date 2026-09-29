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
    """Cache local con TTL, nombres no predecibles y tolerancia a entradas corruptas."""

    def __init__(self, category: str, ttl_hours: float | None = None):
        self.category = category
        default = SETTINGS["cache"]["ttl_hours"].get(category, 24)
        self.ttl = timedelta(hours=ttl_hours if ttl_hours is not None else default)
        self.dir = Path(CACHE_DIR) / category
        self.dir.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str, ext: str) -> Path:
        h = hashlib.sha256(key.encode("utf-8")).hexdigest()
        return self.dir / f"{h}.{ext}"

    def _fresh(self, path: Path) -> bool:
        meta = path.with_suffix(".meta")
        if not path.exists() or not meta.exists():
            return False
        try:
            created = float(json.loads(meta.read_text(encoding="utf-8")).get("created", 0))
            return datetime.now().timestamp() - created <= self.ttl.total_seconds()
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            logger.warning("Entrada de caché corrupta: %s", path)
            return False

    def _stamp(self, path: Path) -> None:
        path.with_suffix(".meta").write_text(
            json.dumps({"created": datetime.now().timestamp()}), encoding="utf-8"
        )

    def get(self, key: str) -> pd.DataFrame | None:
        path = self._path(key, "parquet")
        if not self._fresh(path):
            return None
        try:
            return pd.read_parquet(path)
        except (OSError, ValueError, ImportError) as exc:
            logger.warning("No se pudo leer caché %s: %s", path, exc)
            return None

    def set(self, key: str, df: pd.DataFrame) -> None:
        path = self._path(key, "parquet")
        tmp = path.with_suffix(".tmp.parquet")
        df.to_parquet(tmp, index=False)
        tmp.replace(path)
        self._stamp(path)

    def get_or_fetch(self, key: str, fetch_fn: Callable[[], pd.DataFrame]) -> pd.DataFrame:
        cached = self.get(key)
        if cached is not None:
            return cached
        df = fetch_fn()
        self.set(key, df)
        return df

    def get_json(self, key: str) -> dict | list | None:
        path = self._path(key, "json")
        if not self._fresh(path):
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            logger.warning("JSON de caché inválido: %s", path)
            return None

    def set_json(self, key: str, obj: dict | list) -> None:
        path = self._path(key, "json")
        tmp = path.with_suffix(".tmp.json")
        tmp.write_text(json.dumps(obj), encoding="utf-8")
        tmp.replace(path)
        self._stamp(path)

    def clear_expired(self) -> int:
        removed = 0
        for meta in self.dir.glob("*.meta"):
            try:
                created = float(json.loads(meta.read_text(encoding="utf-8")).get("created", 0))
            except (OSError, ValueError, TypeError, json.JSONDecodeError):
                created = 0
            if datetime.now().timestamp() - created > self.ttl.total_seconds():
                data = meta.with_suffix("")
                for path in (meta, data):
                    if path.exists():
                        path.unlink()
                        removed += 1
        return removed
