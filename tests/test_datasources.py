"""Contract tests for MockDataSource and FlyWireDataSource (auth/import error paths)."""

import sys
import types

import pandas as pd
import pytest

from superfly.datasources.base import DataSource
from superfly.datasources.flybywire import FlyWireDataSource
from superfly.datasources.mock import MockDataSource
from superfly.exceptions import AuthenticationError, RegionNotFoundError

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
        ds.get_annotations("PN", "cell_type")


def test_get_annotations_rejects_unknown_annotation_type():
    ds = FlyWireDataSource()
    with pytest.raises(ValueError, match="Unsupported annotation_type"):
        ds.get_annotations("whatever", "not_a_real_type")


def test_get_region_annotations_raises_when_neuropil_has_no_synapses(monkeypatch):
    class _CaveClientWithEmptyView:
        def __init__(self, dataset):
            self.materialize = types.SimpleNamespace(
                version=None,
                query_view=lambda *a, **kw: pd.DataFrame(
                    columns=["pre_pt_root_id", "post_pt_root_id", "neuropil"]
                ),
            )

    _install_fake_caveclient(monkeypatch, _CaveClientWithEmptyView)
    ds = FlyWireDataSource()
    with pytest.raises(RegionNotFoundError, match="No synapses found in neuropil"):
        ds.get_annotations("NOT_A_NEUROPIL", "region")


def test_get_region_annotations_filters_and_joins_to_annotation_table(monkeypatch):
    synapses = pd.DataFrame(
        {
            # 111 appears 3x, 222 appears 3x, 333 only once (below threshold).
            "pre_pt_root_id": [111, 111, 111, 999, 999, 999],
            "post_pt_root_id": [222, 222, 222, 333, 222, 111],
            "neuropil": ["AL_R"] * 6,
        }
    )

    class _CaveClientWithSynapses:
        def __init__(self, dataset):
            self.materialize = types.SimpleNamespace(
                version=None, query_view=lambda *a, **kw: synapses
            )

    _install_fake_caveclient(monkeypatch, _CaveClientWithSynapses)
    # 999 is deliberately absent from the annotation table (unproofread fragment).
    annotations = pd.DataFrame(
        {"root_id": [111, 222, 333], "cell_type": ["PN", "LN", "KC"]}
    )
    _install_fake_fafbseg(
        monkeypatch, search_annotations=lambda x, verbose=False: annotations
    )

    ds = FlyWireDataSource(region_min_synapses=3)
    result = ds.get_annotations("AL_R", "region")
    assert set(result["root_id"]) == {111, 222}  # 333 below threshold, 999 unannotated


def test_get_annotations_wraps_auth_like_error(monkeypatch):
    _install_fake_caveclient(monkeypatch, _WorkingCaveClient)

    def _raise_auth_error(x, verbose=False):
        raise RuntimeError("403 Forbidden: invalid token")

    _install_fake_fafbseg(monkeypatch, search_annotations=_raise_auth_error)
    ds = FlyWireDataSource()
    with pytest.raises(AuthenticationError):
        ds.get_annotations("PN", "cell_type")


def test_get_annotations_reraises_non_auth_error(monkeypatch):
    _install_fake_caveclient(monkeypatch, _WorkingCaveClient)

    def _raise_other_error(x, verbose=False):
        raise RuntimeError("materialization version not found")

    _install_fake_fafbseg(monkeypatch, search_annotations=_raise_other_error)
    ds = FlyWireDataSource()
    with pytest.raises(RuntimeError, match="materialization version not found"):
        ds.get_annotations("PN", "cell_type")


# ---------------------------------------------------------------------------
# Schema-mapping regressions: FlyWireDataSource must translate canonical
# annotation_type names ("cell_type", "superclass") to the real fafbseg
# column names ("cell_type", "super_class") and the real get_adjacency
# column names (source/target/weight) to our pre/post/syn_count contract.
# These use fake tables shaped exactly like the real schema (confirmed via
# live inspection), so a future fafbseg schema/signature change is caught
# here offline rather than only live in scripts/smoke_test_real_data.py.
# ---------------------------------------------------------------------------


def test_get_annotations_maps_canonical_names_to_real_columns(monkeypatch):
    _install_fake_caveclient(monkeypatch, _WorkingCaveClient)
    real_shaped_table = pd.DataFrame(
        {
            "root_id": [1, 2, 3],
            "cell_type": ["PN", "LN", "PN"],
            "super_class": ["central", "sensory", "central"],
        }
    )
    _install_fake_fafbseg(
        monkeypatch, search_annotations=lambda x, verbose=False: real_shaped_table
    )
    ds = FlyWireDataSource()

    by_cell_type = ds.get_annotations("PN", "cell_type")
    assert set(by_cell_type["root_id"]) == {1, 3}

    # "superclass" (our canonical name) must map to the real "super_class" column.
    by_superclass = ds.get_annotations("sensory", "superclass")
    assert set(by_superclass["root_id"]) == {2}


def test_get_adjacency_renames_columns_and_filters_min_synapses(monkeypatch):
    _install_fake_caveclient(monkeypatch, _WorkingCaveClient)

    def _fake_get_adjacency(sources, targets, square):
        assert square is False  # we rely on long-form, not a pivoted matrix
        return pd.DataFrame(
            {
                "source": [111, 111, 222],
                "target": [222, 333, 333],
                "weight": [10, 2, 7],
            }
        )

    _install_fake_fafbseg(monkeypatch, get_adjacency=_fake_get_adjacency)
    ds = FlyWireDataSource()

    result = ds.get_adjacency([111, 222, 333], min_synapses=5)
    assert list(result.columns) == ["pre", "post", "syn_count"]
    assert set(zip(result["pre"], result["post"])) == {(111, 222), (222, 333)}
    assert (result["syn_count"] >= 5).all()


def test_get_adjacency_wraps_auth_like_error(monkeypatch):
    _install_fake_caveclient(monkeypatch, _WorkingCaveClient)

    def _raise_auth_error(sources, targets, square):
        raise RuntimeError("401 unauthorized")

    _install_fake_fafbseg(monkeypatch, get_adjacency=_raise_auth_error)
    ds = FlyWireDataSource()
    with pytest.raises(AuthenticationError):
        ds.get_adjacency([1, 2, 3])
