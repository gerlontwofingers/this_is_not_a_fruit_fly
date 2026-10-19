"""Offline mock data source for testing and development without FlyWire access."""

import pandas as pd

from superfly.datasources.base import DataSource


class MockDataSource(DataSource):
    """In-memory fixture-backed data source for offline use and testing.

    Contains a small synthetic brain with ~10 neurons and preset connectivity.
    """

    # Synthetic neuron data for the antennal lobe right (AL_R).
    _ANNOTATIONS = pd.DataFrame(
        {
            "root_id": [
                100001,
                100002,
                100003,
                100004,
                100005,
                100006,
                100007,
                100008,
                100009,
                100010,
            ],
            "cell_type": [
                "PN",
                "PN",
                "LN",
                "LN",
                "LN",
                "PN",
                "KC",
                "KC",
                "PN",
                "LN",
            ],
            "region": [
                "AL_R",
                "AL_R",
                "AL_R",
                "AL_R",
                "AL_R",
                "AL_R",
                "MB",
                "MB",
                "AL_R",
                "AL_R",
            ],
            "superclass": [
                "Ascending",
                "Ascending",
                "Local",
                "Local",
                "Local",
                "Ascending",
                "MB",
                "MB",
                "Ascending",
                "Local",
            ],
        }
    )

    # Synthetic adjacency data (long-form).
    _ADJACENCY = pd.DataFrame(
        {
            "pre": [
                100001,
                100001,
                100002,
                100002,
                100003,
                100004,
                100004,
                100005,
                100006,
                100001,
            ],
            "post": [
                100003,
                100004,
                100003,
                100005,
                100007,
                100007,
                100008,
                100008,
                100007,
                100009,
            ],
            "syn_count": [15, 8, 12, 6, 20, 18, 11, 9, 14, 5],
        }
    )

    def get_annotations(self, name: str, annotation_type: str) -> pd.DataFrame:
        """Return synthetic neurons matching the query (case-insensitive partial match)."""
        if annotation_type not in self._ANNOTATIONS.columns:
            return pd.DataFrame(
                columns=["root_id", "cell_type", "region", "superclass"]
            )
        subset = self._ANNOTATIONS[
            self._ANNOTATIONS[annotation_type].str.lower().str.contains(
                name.lower(), na=False
            )
        ].copy()
        return subset if not subset.empty else self._ANNOTATIONS

    def get_adjacency(
        self, neuron_ids: list[int], min_synapses: int = 5
    ) -> pd.DataFrame:
        """Return synthetic adjacency, filtered to the given neurons and min synapse count."""
        adj = self._ADJACENCY[
            (self._ADJACENCY["pre"].isin(neuron_ids))
            & (self._ADJACENCY["post"].isin(neuron_ids))
            & (self._ADJACENCY["syn_count"] >= min_synapses)
        ].copy()
        return adj
