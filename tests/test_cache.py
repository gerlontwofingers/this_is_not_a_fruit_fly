"""Tests for the disk cache decorator and CachedFlyWireDataSource."""

import sys
import types

import pandas as pd

import superfly.cache as cache_module
from superfly.cache import CachedFlyWireDataSource, disk_cached


def test_disk_cached_hits_cache_on_second_call(tmp_path, monkeypatch):
    monkeypatch.setattr(cache_module, "CACHE_DIR", tmp_path)
    calls = []

    class Dummy:
        dataset = "test"
        materialization = 1

        @disk_cached
        def slow(self, x):
            calls.append(x)
            return x * 2

    d = Dummy()
    assert d.slow(3) == 6
    assert d.slow(3) == 6
    assert calls == [3]  # second call served from disk, not recomputed


def test_disk_cached_misses_for_different_args(tmp_path, monkeypatch):
    monkeypatch.setattr(cache_module, "CACHE_DIR", tmp_path)
    calls = []

    class Dummy:
        dataset = "test"
        materialization = 1

        @disk_cached
        def slow(self, x):
            calls.append(x)
            return x * 2

    d = Dummy()
    d.slow(1)
    d.slow(2)
    assert calls == [1, 2]


def test_disk_cached_key_varies_by_instance_config(tmp_path, monkeypatch):
    monkeypatch.setattr(cache_module, "CACHE_DIR", tmp_path)
    calls = []

    class Dummy:
        def __init__(self, dataset, materialization):
            self.dataset = dataset
            self.materialization = materialization

        @disk_cached
        def slow(self, x):
            calls.append((self.dataset, x))
            return x

    Dummy("a", 1).slow(5)
    Dummy("b", 1).slow(5)
    assert calls == [("a", 5), ("b", 5)]  # different config -> cache miss for both


def test_disk_cached_writes_pickle_file_to_cache_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(cache_module, "CACHE_DIR", tmp_path)

    class Dummy:
        dataset = "test"
        materialization = 1

        @disk_cached
        def slow(self, x):
            return x

    Dummy().slow(42)
    assert list(tmp_path.glob("*.pkl"))


def test_cached_flywire_datasource_caches_across_instances(tmp_path, monkeypatch):
    monkeypatch.setattr(cache_module, "CACHE_DIR", tmp_path)
    calls = []

    def _fake_search_annotations(x, verbose=False):
        calls.append(x)
        return pd.DataFrame({"root_id": [1, 2], "cell_type": ["PN", "LN"]})

    fake_flywire = types.ModuleType("fafbseg.flywire")
    fake_flywire.search_annotations = _fake_search_annotations
    fake_fafbseg = types.ModuleType("fafbseg")
    fake_fafbseg.flywire = fake_flywire
    monkeypatch.setitem(sys.modules, "fafbseg", fake_fafbseg)
    monkeypatch.setitem(sys.modules, "fafbseg.flywire", fake_flywire)

    class _FakeCaveClient:
        def __init__(self, dataset):
            self.materialize = types.SimpleNamespace(version=None)

    fake_caveclient = types.ModuleType("caveclient")
    fake_caveclient.CAVEclient = _FakeCaveClient
    monkeypatch.setitem(sys.modules, "caveclient", fake_caveclient)

    # Two separate instances with matching dataset/materialization share a cache key.
    CachedFlyWireDataSource().get_annotations("PN", "cell_type")
    CachedFlyWireDataSource().get_annotations("PN", "cell_type")
    assert calls == [None]  # search_annotations(None) only invoked once (cache hit on 2nd)
