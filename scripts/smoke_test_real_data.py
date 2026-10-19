#!/usr/bin/env python
"""Manual smoke test against the real FlyWire/CAVE API.

Not part of the pytest suite -- requires a configured CAVE auth token (see
docs/SETUP.md). Run directly: `uv run python scripts/smoke_test_real_data.py`

Exercises get_annotations/get_adjacency/FlyBrain.load_cell_type against live
data, to catch fafbseg/CAVE API drift (signature or schema changes) that the
offline mock-backed test suite can't detect.
"""

from __future__ import annotations

import sys
import time

from superfly import FlyBrain
from superfly.datasources.flybywire import FlyWireDataSource
from superfly.exceptions import RegionNotFoundError


def _step(name: str):
    print(f"\n=== {name} ===")


def main() -> int:
    ds = FlyWireDataSource()

    _step("client auth")
    ds.client
    print(f"OK: authenticated against datastack {ds.dataset!r}")

    _step("get_annotations(cell_type)")
    t0 = time.time()
    annotations = ds.get_annotations("PN", "cell_type")
    assert "root_id" in annotations.columns
    assert not annotations.empty
    print(f"OK: {len(annotations)} rows in {time.time() - t0:.1f}s")

    _step("get_annotations(superclass)")
    t0 = time.time()
    superclass = ds.get_annotations("central", "superclass")
    assert not superclass.empty
    print(f"OK: {len(superclass)} rows in {time.time() - t0:.1f}s")

    _step("get_annotations(region) raises RegionNotFoundError")
    try:
        ds.get_annotations("AL_R", "region")
        print("FAIL: expected RegionNotFoundError, none raised")
        return 1
    except RegionNotFoundError:
        print("OK: RegionNotFoundError raised as expected")

    _step("get_adjacency")
    neuron_ids = annotations["root_id"].tolist()[:15]
    t0 = time.time()
    adjacency = ds.get_adjacency(neuron_ids, min_synapses=1)
    assert list(adjacency.columns) == ["pre", "post", "syn_count"]
    print(f"OK: {len(adjacency)} edges in {time.time() - t0:.1f}s")

    _step("FlyBrain.load_cell_type end-to-end")
    t0 = time.time()
    brain = FlyBrain(datasource=ds).load_cell_type(
        annotations["cell_type"].iloc[0], min_synapses=1
    )
    dense = brain.to_numpy()
    print(f"OK: {brain} -> to_numpy shape {dense.shape} in {time.time() - t0:.1f}s")

    print("\nAll real-data smoke tests passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
