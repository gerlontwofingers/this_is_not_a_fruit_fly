"""FlyWire/CAVE-backed data source (requires the `flywire` extra and a configured CAVE auth token)."""

from __future__ import annotations

import pandas as pd

from superfly.datasources.base import DataSource
from superfly.exceptions import AuthenticationError

_INSTALL_HINT = (
    "FlyWireDataSource requires the 'flywire' extra. "
    "Install with: pip install superfly[flywire]"
)
_AUTH_HINT = (
    "CAVE/FlyWire authentication failed. See docs/SETUP.md for how to "
    "register and configure a CAVE auth token."
)


class FlyWireDataSource(DataSource):
    """Live data source backed by FlyWire/FAFB via fafbseg and CAVEclient."""

    def __init__(self, dataset: str = "fafb", materialization: int = 783):
        self.dataset = dataset
        self.materialization = materialization
        self._client = None

    @property
    def client(self):
        """Lazily construct and authenticate the CAVEclient."""
        if self._client is None:
            try:
                from caveclient import CAVEclient
            except ImportError as e:
                raise ImportError(_INSTALL_HINT) from e
            try:
                client = CAVEclient("flywire_fafb_production")
                client.materialize.version = self.materialization
            except Exception as e:
                raise AuthenticationError(_AUTH_HINT) from e
            self._client = client
        return self._client

    def get_annotations(self, name: str, annotation_type: str) -> pd.DataFrame:
        try:
            from fafbseg import flywire
        except ImportError as e:
            raise ImportError(_INSTALL_HINT) from e
        self.client  # ensure auth happens before querying
        try:
            return flywire.search_annotations(name, annotation_type=annotation_type)
        except Exception as e:
            if self._looks_like_auth_error(e):
                raise AuthenticationError(_AUTH_HINT) from e
            raise

    def get_adjacency(
        self, neuron_ids: list[int], min_synapses: int = 5
    ) -> pd.DataFrame:
        try:
            from fafbseg import flywire
        except ImportError as e:
            raise ImportError(_INSTALL_HINT) from e
        self.client  # ensure auth happens before querying
        try:
            return flywire.get_adjacency(
                sources=neuron_ids,
                targets=neuron_ids,
                min_synapses=min_synapses,
                square=False,
            )
        except Exception as e:
            if self._looks_like_auth_error(e):
                raise AuthenticationError(_AUTH_HINT) from e
            raise

    @staticmethod
    def _looks_like_auth_error(error: Exception) -> bool:
        """Heuristic for distinguishing auth failures from other fafbseg/CAVE errors."""
        message = str(error).lower()
        return any(
            token in message
            for token in ("401", "403", "unauthorized", "authentication", "token")
        )
