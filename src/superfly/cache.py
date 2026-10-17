"""Disk cache for expensive FlyWireDataSource queries."""

from __future__ import annotations

import hashlib
import pickle
from functools import wraps
from pathlib import Path
from typing import Any, Callable

from superfly.datasources.flybywire import FlyWireDataSource

CACHE_DIR = Path.home() / ".cache" / "superfly"


def _cache_key(func_name: str, self: Any, args: tuple, kwargs: dict) -> str:
    """Build a stable hash key from the method name, instance config, and call args."""
    instance_key = (getattr(self, "dataset", ""), getattr(self, "materialization", ""))
    raw = repr((func_name, instance_key, args, sorted(kwargs.items())))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def disk_cached(func: Callable) -> Callable:
    """Decorator caching a bound method's return value to a pickle file on disk."""

    @wraps(func)
    def wrapper(self, *args, **kwargs):
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        key = _cache_key(func.__name__, self, args, kwargs)
        cache_file = CACHE_DIR / f"{key}.pkl"
        if cache_file.exists():
            with cache_file.open("rb") as f:
                return pickle.load(f)
        result = func(self, *args, **kwargs)
        with cache_file.open("wb") as f:
            pickle.dump(result, f)
        return result

    return wrapper


class CachedFlyWireDataSource(FlyWireDataSource):
    """FlyWireDataSource with disk-backed caching of annotation/adjacency queries.

    Mock data sources are intentionally never cached — only real, slow/rate-limited
    CAVE queries benefit from this.
    """

    get_annotations = disk_cached(FlyWireDataSource.get_annotations)
    get_adjacency = disk_cached(FlyWireDataSource.get_adjacency)
