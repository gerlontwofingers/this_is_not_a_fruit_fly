"""Abstract data source interface for fetching neuron annotations and connectivity."""

from abc import ABC, abstractmethod

import pandas as pd


class DataSource(ABC):
    """Interface for fetching neuron annotations and adjacency data.

    Implementations may hit a live service (e.g. FlyWire/CAVE) or return
    fixture data for offline use and testing. `FlyBrain` depends only on
    this interface, never on a concrete implementation.
    """

    @abstractmethod
    def get_annotations(self, name: str, annotation_type: str) -> pd.DataFrame:
        """Return neuron metadata matching `name` under the given `annotation_type`.

        annotation_type: e.g. 'region', 'cell_type', 'superclass'.
        Must include a 'root_id' column identifying each neuron.
        """
        raise NotImplementedError

    @abstractmethod
    def get_adjacency(
        self, neuron_ids: list[int], min_synapses: int = 5
    ) -> pd.DataFrame:
        """Return a long-form adjacency DataFrame for the given neuron IDs.

        Must include 'pre', 'post', and 'syn_count' columns, filtered to
        edges with `syn_count >= min_synapses`.
        """
        raise NotImplementedError
