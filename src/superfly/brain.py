"""Core graph object: loads fly connectome subsets and exports them as graphs/tensors."""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix

from superfly.datasources.base import DataSource
from superfly.exceptions import EmptyGraphError

_TORCH_HINT = (
    "This export requires the 'torch' extra. "
    "Install with: pip install superfly[torch]"
)
_VIZ_HINT = (
    "This export requires the 'viz' extra. Install with: pip install superfly[viz]"
)


class FlyBrain:
    """A connectome subgraph: neuron metadata plus a sparse synaptic adjacency matrix."""

    def __init__(self, datasource: DataSource | None = None):
        if datasource is None:
            from superfly.cache import CachedFlyWireDataSource

            datasource = CachedFlyWireDataSource()
        self.datasource = datasource
        self.neurons: pd.DataFrame | None = None
        self.neuron_ids: list[int] = []
        self.adj: csr_matrix | None = None
        self.weights: np.ndarray | None = None

    # -----------------------------------------------------------------
    # LOADING
    # -----------------------------------------------------------------

    def load_region(self, region_name: str, min_synapses: int = 5) -> FlyBrain:
        """Load all neurons annotated to a brain region (e.g. 'AL_R', 'MB', 'LO')."""
        return self._load(region_name, "region", min_synapses)

    def load_cell_type(self, cell_type_name: str, min_synapses: int = 5) -> FlyBrain:
        """Load all neurons of a given cell type."""
        return self._load(cell_type_name, "cell_type", min_synapses)

    def load_superclass(self, superclass_name: str, min_synapses: int = 5) -> FlyBrain:
        """Load all neurons of a given superclass."""
        return self._load(superclass_name, "superclass", min_synapses)

    def _load(self, query: str, annotation_type: str, min_synapses: int) -> FlyBrain:
        annotations = self.datasource.get_annotations(query, annotation_type)
        if annotations is None or annotations.empty:
            raise EmptyGraphError(
                f"No neurons found for {annotation_type}={query!r}."
            )
        neuron_ids = annotations["root_id"].unique().tolist()
        adj_df = self.datasource.get_adjacency(neuron_ids, min_synapses=min_synapses)

        self.neurons = annotations
        self.neuron_ids = neuron_ids
        self.adj = self._build_adjacency(neuron_ids, adj_df)
        self.weights = self.adj.data
        return self

    @staticmethod
    def _build_adjacency(neuron_ids: list[int], adj_df: pd.DataFrame) -> csr_matrix:
        """Build a sparse neuron-by-neuron synapse-count matrix from long-form edges."""
        n = len(neuron_ids)
        if n == 0:
            raise EmptyGraphError("Cannot build adjacency from an empty neuron set.")

        id_to_idx = {nid: i for i, nid in enumerate(neuron_ids)}
        if adj_df is None or adj_df.empty:
            return csr_matrix((n, n), dtype=np.int64)

        rows = adj_df["pre"].map(id_to_idx)
        cols = adj_df["post"].map(id_to_idx)
        # Edges touching neurons outside the loaded set map to NaN and are dropped.
        keep = rows.notna() & cols.notna()
        rows, cols = rows[keep].astype(int), cols[keep].astype(int)
        data = adj_df.loc[keep, "syn_count"].to_numpy()

        return csr_matrix((data, (rows, cols)), shape=(n, n))

    # -----------------------------------------------------------------
    # EXPORTS
    # -----------------------------------------------------------------

    def to_numpy(self) -> np.ndarray:
        """Return the adjacency as a dense array. WARNING: memory-hungry on big graphs."""
        return self._require_loaded().toarray()

    def to_networkx(self):
        """Return a networkx DiGraph. WARNING: slow for big graphs."""
        try:
            import networkx as nx
        except ImportError as e:
            raise ImportError(_VIZ_HINT) from e
        return nx.from_scipy_sparse_array(
            self._require_loaded(), create_using=nx.DiGraph
        )

    def to_pyg(self):
        """Return a PyTorch Geometric `Data` object with edge weights as `edge_attr`."""
        try:
            import torch
            from torch_geometric.data import Data
        except ImportError as e:
            raise ImportError(_TORCH_HINT) from e

        coo = self._require_loaded().tocoo()
        edge_index = torch.tensor(
            np.vstack([coo.row, coo.col]), dtype=torch.long
        )
        edge_attr = torch.tensor(coo.data, dtype=torch.float)
        return Data(edge_index=edge_index, edge_attr=edge_attr, num_nodes=coo.shape[0])

    def mask(self, tensor):
        """Zero out entries of `tensor` where the fly has no corresponding connection."""
        try:
            import torch
        except ImportError as e:
            raise ImportError(_TORCH_HINT) from e
        connectivity = torch.tensor(self.to_numpy(), dtype=torch.bool)
        return tensor * connectivity

    def _require_loaded(self) -> csr_matrix:
        if self.adj is None:
            raise EmptyGraphError(
                "No graph loaded. Call load_region/load_cell_type/load_superclass first."
            )
        return self.adj

    def __repr__(self) -> str:
        n = len(self.neuron_ids)
        edges = self.adj.nnz if self.adj is not None else 0
        return f"<FlyBrain neurons={n} edges={edges}>"
