"""Pytest fixtures for superfly tests."""

import pytest

from superfly.datasources import MockDataSource


@pytest.fixture
def mock_annotations():
    """Synthetic neuron metadata for testing (~10 neurons)."""
    return MockDataSource._ANNOTATIONS.copy()


@pytest.fixture
def mock_adjacency():
    """Synthetic synaptic connectivity for testing."""
    return MockDataSource._ADJACENCY.copy()


@pytest.fixture
def mock_datasource():
    """A MockDataSource instance for offline tests."""
    return MockDataSource()


@pytest.fixture
def sample_neuron_ids(mock_annotations):
    """Sample of neuron IDs from the mock dataset."""
    return mock_annotations["root_id"].tolist()[:5]
