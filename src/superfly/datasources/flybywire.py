"""FlyWire/CAVE-backed data source (requires the `flywire` extra and a configured CAVE auth token)."""

from __future__ import annotations

import pandas as pd

from superfly.datasources.base import DataSource
from superfly.exceptions import AuthenticationError, RegionNotFoundError

_INSTALL_HINT = (
    "FlyWireDataSource requires the 'flywire' extra. "
    "Install with: pip install superfly[flywire]"
)
_AUTH_HINT = (
    "CAVE/FlyWire authentication failed. See docs/SETUP.md for how to "
    "register and configure a CAVE auth token."
)
_REGION_UNSUPPORTED_HINT = (
    "Region-based loading is not supported against real FlyWire data: the "
    "real hierarchical annotation table has no per-neuron 'region' column "
    "(MockDataSource's fixture schema has one only for testing convenience). "
    "Use load_cell_type()/load_superclass() against real data, or use "
    "MockDataSource for region-based examples."
)


class FlyWireDataSource(DataSource):
    """Live data source backed by FlyWire/FAFB via fafbseg and CAVEclient.

    `dataset` is the CAVE *datastack* name (e.g. "flywire_fafb_public",
    "flywire_fafb_production") — it must match a datastack your CAVE account
    actually has `view` permission for, which varies by account. Most
    external accounts have public dataset access rather than the restricted
    production datastack. Call `CAVEclient().info.get_datastacks()` to list
    all valid datastack names if `client` raises an AuthenticationError.
    """

    def __init__(self, dataset: str = "flywire_fafb_public", materialization: int = 783):
        self.dataset = dataset
        self.materialization = materialization
        self._client = None

    # Canonical annotation_type (used by FlyBrain/MockDataSource) -> real
    # fafbseg hierarchical-annotation-table column name. "region" is
    # intentionally absent: the real table has no per-neuron region column.
    _ANNOTATION_COLUMN_MAP = {
        "cell_type": "cell_type",
        "superclass": "super_class",
    }

    @property
    def client(self):
        """Lazily construct and authenticate the CAVEclient."""
        if self._client is None:
            try:
                from caveclient import CAVEclient
            except ImportError as e:
                raise ImportError(_INSTALL_HINT) from e
            try:
                client = CAVEclient(self.dataset)
                client.materialize.version = self.materialization
            except Exception as e:
                raise AuthenticationError(_AUTH_HINT) from e
            self._client = client
        return self._client

    def get_annotations(self, name: str, annotation_type: str) -> pd.DataFrame:
        if annotation_type not in self._ANNOTATION_COLUMN_MAP:
            raise RegionNotFoundError(_REGION_UNSUPPORTED_HINT)
        column = self._ANNOTATION_COLUMN_MAP[annotation_type]
        try:
            from fafbseg import flywire
        except ImportError as e:
            raise ImportError(_INSTALL_HINT) from e
        self.client  # ensure auth happens before querying
        try:
            # search_annotations() has no column filter of its own (it's a
            # free-text search across all annotation columns combined), so
            # fetch the full table (fafbseg caches it on disk) and filter
            # client-side by the mapped column, mirroring MockDataSource.
            table = flywire.search_annotations(None, verbose=False)
        except Exception as e:
            if self._looks_like_auth_error(e):
                raise AuthenticationError(_AUTH_HINT) from e
            raise
        matches = table[column].astype(str).str.contains(name, case=False, na=False)
        return table[matches]

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
