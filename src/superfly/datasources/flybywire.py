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
_REGION_NOT_FOUND_HINT = (
    "No synapses found in neuropil {name!r}. Region names are exact CAVE "
    "neuropil names (e.g. 'AL_R', 'MB_CA_L', 'LH_R', 'EB', 'GNG') \u2014 they are "
    "case-sensitive and side-suffixed. See docs/SETUP.md for how to list "
    "the available neuropil names."
)

# CAVE view joining synapses to their assigned neuropil. Unlike the
# hierarchical annotation table (which has no region column at all), this
# supports the reverse lookup: neuropil -> the neurons synapsing in it.
_NEUROPIL_VIEW = "valid_synapses_nt_np_v6"


class FlyWireDataSource(DataSource):
    """Live data source backed by FlyWire/FAFB via fafbseg and CAVEclient.

    `dataset` is the CAVE *datastack* name (e.g. "flywire_fafb_public",
    "flywire_fafb_production") — it must match a datastack your CAVE account
    actually has `view` permission for, which varies by account. Most
    external accounts have public dataset access rather than the restricted
    production datastack. Call `CAVEclient().info.get_datastacks()` to list
    all valid datastack names if `client` raises an AuthenticationError.

    Region lookups are approximate — see `get_annotations` for the caveats
    and the two tuning knobs (`region_synapse_limit`, `region_min_synapses`).
    """

    def __init__(
        self,
        dataset: str = "flywire_fafb_public",
        materialization: int = 783,
        region_synapse_limit: int = 50_000,
        region_min_synapses: int = 5,
    ):
        self.dataset = dataset
        self.materialization = materialization
        self.region_synapse_limit = region_synapse_limit
        self.region_min_synapses = region_min_synapses
        self._client = None

    # Canonical annotation_type (used by FlyBrain/MockDataSource) -> real
    # fafbseg hierarchical-annotation-table column name. "region" is absent
    # here because the annotation table has no region column; it's served
    # from synapse/neuropil data instead (see _get_region_annotations).
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
        """Return annotated neurons matching `name` for the given annotation type.

        `region` lookups are approximate: the hierarchical annotation table has
        no region column, so they're derived from synapse-to-neuropil data by
        sampling up to `region_synapse_limit` synapses in that neuropil and
        keeping neurons with at least `region_min_synapses` of them. Large
        neuropils have more synapses than the sample, so the result is a subset
        biased toward densely-connected neurons. Raise `region_synapse_limit`
        for better coverage at the cost of (substantially) slower queries.
        """
        if annotation_type == "region":
            return self._get_region_annotations(name)
        if annotation_type not in self._ANNOTATION_COLUMN_MAP:
            raise ValueError(
                f"Unsupported annotation_type {annotation_type!r}. Expected "
                f"'region' or one of {sorted(self._ANNOTATION_COLUMN_MAP)}."
            )
        column = self._ANNOTATION_COLUMN_MAP[annotation_type]
        table = self._annotation_table()
        matches = table[column].astype(str).str.contains(name, case=False, na=False)
        return table[matches]

    def _annotation_table(self) -> pd.DataFrame:
        """Fetch the full hierarchical annotation table (fafbseg caches it on disk)."""
        try:
            from fafbseg import flywire
        except ImportError as e:
            raise ImportError(_INSTALL_HINT) from e
        self.client  # ensure auth happens before querying
        try:
            # search_annotations() has no column filter of its own (it's a
            # free-text search across all annotation columns combined), so
            # fetch the whole table and filter client-side, like MockDataSource.
            return flywire.search_annotations(None, verbose=False)
        except Exception as e:
            if self._looks_like_auth_error(e):
                raise AuthenticationError(_AUTH_HINT) from e
            raise

    def _get_region_annotations(self, name: str) -> pd.DataFrame:
        """Resolve a neuropil name to annotated neurons synapsing in that region."""
        try:
            synapses = self.client.materialize.query_view(
                _NEUROPIL_VIEW,
                filter_equal_dict={"neuropil": name},
                select_columns=["pre_pt_root_id", "post_pt_root_id", "neuropil"],
                limit=self.region_synapse_limit,
            )
        except Exception as e:
            if self._looks_like_auth_error(e):
                raise AuthenticationError(_AUTH_HINT) from e
            raise
        if synapses.empty:
            raise RegionNotFoundError(_REGION_NOT_FOUND_HINT.format(name=name))

        # A neuron counts as "in" the region whether it sends or receives there.
        endpoints = pd.concat(
            [synapses["pre_pt_root_id"], synapses["post_pt_root_id"]]
        )
        counts = endpoints.value_counts()
        in_region = set(counts[counts >= self.region_min_synapses].index)

        # Joining against the annotation table drops unproofread fragments,
        # which make up a large share of raw synapse endpoints.
        table = self._annotation_table()
        return table[table["root_id"].isin(in_region)]

    def get_adjacency(
        self, neuron_ids: list[int], min_synapses: int = 5
    ) -> pd.DataFrame:
        try:
            from fafbseg import flywire
        except ImportError as e:
            raise ImportError(_INSTALL_HINT) from e
        self.client  # ensure auth happens before querying
        try:
            # get_adjacency() has no min_synapses filter of its own (it has
            # min_score, a synapse-confidence threshold -- a different
            # concept) and returns source/target/weight columns, not our
            # pre/post/syn_count contract. Rename and filter client-side.
            adj = flywire.get_adjacency(
                sources=neuron_ids,
                targets=neuron_ids,
                square=False,
            )
        except Exception as e:
            if self._looks_like_auth_error(e):
                raise AuthenticationError(_AUTH_HINT) from e
            raise
        adj = adj.rename(columns={"source": "pre", "target": "post", "weight": "syn_count"})
        return adj[adj["syn_count"] >= min_synapses].reset_index(drop=True)

    @staticmethod
    def _looks_like_auth_error(error: Exception) -> bool:
        """Heuristic for distinguishing auth failures from other fafbseg/CAVE errors."""
        message = str(error).lower()
        return any(
            token in message
            for token in ("401", "403", "unauthorized", "authentication", "token")
        )
