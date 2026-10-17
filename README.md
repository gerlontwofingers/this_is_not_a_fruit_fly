# this_is_not_a_fruit_fly

This is an exploration of a simulation of a fruit fly's brain. Weird.

## superfly

`superfly` is a small toolkit for building graph/tensor views on top of the
[FlyWire](https://flywire.ai/) fruit fly connectome — the full synapse-level
wiring diagram of the *Drosophila melanogaster* brain. It loads neuron
subsets by region, cell type, or superclass, and exports them as sparse
matrices, dense arrays, [PyTorch Geometric](https://pytorch-geometric.readthedocs.io/)
graphs, or [networkx](https://networkx.org/) graphs for downstream analysis
and experiments.

Real connectome queries go through [fafbseg](https://fafbseg-py.readthedocs.io/)
and [CAVEclient](https://caveclient.readthedocs.io/) (requires a FlyWire/CAVE
account — see [docs/SETUP.md](docs/SETUP.md)) and are disk-cached locally
since they're slow/rate-limited. For development, testing, or just poking
around without an account, an offline `MockDataSource` provides a small
synthetic fixture brain with no network access required.

### Install

Base install (core graph object only, no real-data or export backends):

```bash
pip install -e .
```

With optional extras, as needed:

```bash
# Real FlyWire/CAVE data access
pip install -e ".[flywire]"

# PyTorch Geometric export (`to_pyg`, `mask`)
pip install -e ".[torch]"

# networkx export (`to_networkx`)
pip install -e ".[viz]"

# Everything
pip install -e ".[flywire,torch,viz]"
```

### Quickstart (offline, no FlyWire account needed)

```python
from superfly import FlyBrain
from superfly.datasources import MockDataSource

# MockDataSource ships a small synthetic ~10-neuron fixture brain.
brain = FlyBrain(datasource=MockDataSource()).load_region("AL_R")
print(brain)  # <FlyBrain neurons=8 edges=5>

dense = brain.to_numpy()        # dense adjacency matrix
graph = brain.to_networkx()     # networkx.DiGraph (requires the `viz` extra)
```

You can also load by cell type or superclass:

```python
brain = FlyBrain(datasource=MockDataSource()).load_cell_type("PN")
brain = FlyBrain(datasource=MockDataSource()).load_superclass("Local")
```

### Using real FlyWire data

Omit the `datasource` argument to default to a disk-cached `FlyWireDataSource`,
once you've set up CAVE auth (see [docs/SETUP.md](docs/SETUP.md)):

```python
from superfly import FlyBrain

brain = FlyBrain().load_region("AL_R")
```

### Testing

```bash
uv sync
uv run pytest -v
```

The test suite runs fully offline against `MockDataSource` — no FlyWire
account or network access required.

