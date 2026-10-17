"""Contract tests for MockDataSource and FlyWireDataSource (auth/import error paths)."""

import sys
import types

import pytest

from superfly.datasources.base import DataSource
from superfly.datasources.flybywire import FlyWireDataSource
from superfly.datasources.mock import MockDataSource
from superfly.exceptions import AuthenticationError

# ---------------------------------------------------------------------------
# MockDataSource contract
# ---------------------------------------------------------------------------


def test_mock_datasource_is_a_datasource(mock_datasource):
    assert isinstance(mock_datasource, DataSource)


def test_mock_get_annotations_returns_root_id_column(mock_datasource):
    result = mock_datasource.get_annotations("AL_R", "region")
    assert "root_id" in result.columns
    assert not result.empty


def test_mock_get_annotations_filters_by_substring(mock_datasource):
    result = mock_datasource.get_annotations("mb", "region")
    assert set(result["region"]) == {"MB"}


def test_mock_get_adjacency_returns_expected_columns(mock_datasource, sample_neuron_ids):
    result = mock_datasource.get_adjacency(sample_neuron_ids)
    assert list(result.columns) == ["pre", "post", "syn_count"]


def test_mock_get_adjacency_filters_by_neurons_and_min_synapses(mock_datasource):
    result = mock_datasource.get_adjacency([100001, 100003, 100004], min_synapses=10)
    assert all(result["pre"].isin([100001, 100003, 100004]))
    assert all(result["post"].isin([100001, 100003, 100004]))
    assert all(result["syn_count"] >= 10)


# ---------------------------------------------------------------------------
# FlyWireDataSource: import-guard and auth-error paths (fully offline, via
# fake modules injected into sys.modules — no real fafbseg/caveclient needed)
# ---------------------------------------------------------------------------


def _install_fake_caveclient(monkeypatch, client_cls):
    fake_module = types.ModuleType("caveclient")
    fake_module.CAVEclient = client_cls
    monkeypatch.setitem(sys.modules, "caveclient", fake_module)


def _install_fake_fafbseg(monkeypatch, search_annotations=None, get_adjacency=None):
    fake_flywire = types.ModuleType("fafbseg.flywire")
    fake_flywire.search_annotations = search_annotations
    fake_flywire.get_adjacency = get_adjacency
    fake_fafbseg = types.ModuleType("fafbseg")
    fake_fafbseg.flywire = fake_flywire
    monkeypatch.setitem(sys.modules, "fafbseg", fake_fafbseg)
    monkeypatch.setitem(sys.modules, "fafbseg.flywire", fake_flywire)


class _WorkingCaveClient:
    """Fake CAVEclient that authenticates successfully."""

    def __init__(self, dataset):
        self.materialize = types.SimpleNamespace(version=None)


def test_client_property_raises_authentication_error_on_failure(monkeypatch):
    class _FailingCaveClient:
        def __init__(self, dataset):
            raise RuntimeError("401 Unauthorized")

    _install_fake_caveclient(monkeypatch, _FailingCaveClient)
    ds = FlyWireDataSource()
    with pytest.raises(AuthenticationError):
        ds.client


def test_client_property_raises_import_error_when_caveclient_missing(monkeypatch):
    monkeypatch.setitem(sys.modules, "caveclient", None)
    ds = FlyWireDataSource()
    with pytest.raises(ImportError, match=r"superfly\[flywire\]"):
        ds.client


def test_get_annotations_raises_import_error_when_fafbseg_missing(monkeypatch):
    monkeypatch.setitem(sys.modules, "fafbseg", None)
    ds = FlyWireDataSource()
    with pytest.raises(ImportError, match=r"superfly\[flywire\]"):
        ds.get_annotations("AL_R", "region")


def test_get_annotations_wraps_auth_like_error(monkeypatch):
    _install_fake_caveclient(monkeypatch, _WorkingCaveClient)

    def _raise_auth_error(name, annotation_type=None):
        raise RuntimeError("403 Forbidden: invalid token")

    _install_fake_fafbseg(monkeypatch, search_annotations=_raise_auth_error)
    ds = FlyWireDataSource()
    with pytest.raises(AuthenticationError):
        ds.get_annotations("AL_R", "region")


def test_get_annotations_reraises_non_auth_error(monkeypatch):
    _install_fake_caveclient(monkeypatch, _WorkingCaveClient)

    def _raise_other_error(name, annotation_type=None):
        raise RuntimeError("materialization version not found")

    _install_fake_fafbseg(monkeypatch, search_annotations=_raise_other_error)
    ds = FlyWireDataSource()
    with pytest.raises(RuntimeError, match="materialization version not found"):
        ds.get_annotations("AL_R", "region")


def test_get_adjacency_wraps_auth_like_error(monkeypatch):
    _install_fake_caveclient(monkeypatch, _WorkingCaveClient)

    def _raise_auth_error(sources, targets, min_synapses, square):
        raise RuntimeError("401 unauthorized")

    _install_fake_fafbseg(monkeypatch, get_adjacency=_raise_auth_error)
    ds = FlyWireDataSource()
    with pytest.raises(AuthenticationError):
        ds.get_adjacency([1, 2, 3])
