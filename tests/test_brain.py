"""Tests for FlyBrain loading and export methods, using MockDataSource."""

import numpy as np
import pandas as pd
import pytest

from superfly.brain import FlyBrain
from superfly.datasources.base import DataSource
from superfly.exceptions import EmptyGraphError


class _EmptyDataSource(DataSource):
    """Stub datasource returning no annotations, for testing FlyBrain's empty-result guard."""

    def get_annotations(self, name, annotation_type):
        return pd.DataFrame(columns=["root_id"])

    def get_adjacency(self, neuron_ids, min_synapses=5):
        return pd.DataFrame(columns=["pre", "post", "syn_count"])


def test_load_region_populates_neurons_and_adjacency(mock_datasource):
    brain = FlyBrain(datasource=mock_datasource).load_region("AL_R")
    assert len(brain.neuron_ids) == 8
    assert brain.neurons is not None
    assert set(brain.neurons["root_id"]) == set(brain.neuron_ids)
    assert brain.adj.shape == (8, 8)


def test_load_region_default_min_synapses(mock_datasource):
    brain = FlyBrain(datasource=mock_datasource).load_region("AL_R")
    # Edges among AL_R neurons with syn_count >= 5 (default threshold).
    assert brain.adj.nnz == 5
    assert brain.weights.min() >= 5


def test_load_region_min_synapses_filter(mock_datasource):
    brain = FlyBrain(datasource=mock_datasource).load_region("AL_R", min_synapses=15)
    assert brain.adj.nnz == 1
    assert brain.weights.min() >= 15


def test_load_cell_type(mock_datasource):
    brain = FlyBrain(datasource=mock_datasource).load_cell_type("PN")
    assert len(brain.neuron_ids) == 4
    assert set(brain.neurons["cell_type"]) == {"PN"}


def test_load_superclass(mock_datasource):
    brain = FlyBrain(datasource=mock_datasource).load_superclass("Local")
    assert len(brain.neuron_ids) == 4
    assert set(brain.neurons["superclass"]) == {"Local"}


def test_load_no_matching_neurons_raises():
    with pytest.raises(EmptyGraphError):
        FlyBrain(datasource=_EmptyDataSource()).load_region("nonexistent_region_xyz")


def test_to_numpy_shape_and_values(mock_datasource):
    brain = FlyBrain(datasource=mock_datasource).load_region("AL_R")
    dense = brain.to_numpy()
    assert isinstance(dense, np.ndarray)
    assert dense.shape == (8, 8)
    assert dense.sum() == brain.weights.sum()


def test_to_numpy_without_loading_raises(mock_datasource):
    brain = FlyBrain(datasource=mock_datasource)
    with pytest.raises(EmptyGraphError):
        brain.to_numpy()


def test_to_networkx_produces_directed_graph(mock_datasource):
    nx = pytest.importorskip("networkx")
    brain = FlyBrain(datasource=mock_datasource).load_region("AL_R")
    graph = brain.to_networkx()
    assert isinstance(graph, nx.DiGraph)
    assert graph.number_of_nodes() == 8
    assert graph.number_of_edges() == brain.adj.nnz


def test_to_pyg_returns_expected_data(mock_datasource):
    pytest.importorskip("torch")
    pytest.importorskip("torch_geometric")
    brain = FlyBrain(datasource=mock_datasource).load_region("AL_R")
    data = brain.to_pyg()
    assert data.num_nodes == 8
    assert data.edge_index.shape[0] == 2
    assert data.edge_attr.shape[0] == brain.adj.nnz


def test_mask_zeroes_unconnected_entries(mock_datasource):
    torch = pytest.importorskip("torch")
    brain = FlyBrain(datasource=mock_datasource).load_region("AL_R")
    ones = torch.ones((8, 8), dtype=torch.float)
    masked = brain.mask(ones)
    connectivity = torch.tensor(brain.to_numpy(), dtype=torch.bool)
    assert torch.equal(masked, ones * connectivity)
    assert masked.sum().item() == brain.adj.nnz


def test_repr_reports_neuron_and_edge_counts(mock_datasource):
    brain = FlyBrain(datasource=mock_datasource).load_region("AL_R")
    rep = repr(brain)
    assert "neurons=8" in rep
    assert f"edges={brain.adj.nnz}" in rep
