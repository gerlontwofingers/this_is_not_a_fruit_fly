# Setup: FlyWire / CAVE Access

`superfly`'s `FlyWireDataSource` talks to the real FlyWire connectome via
[fafbseg](https://fafbseg-py.readthedocs.io/) and
[CAVEclient](https://caveclient.readthedocs.io/). This is a one-time, manual
setup step tied to your own FlyWire/CAVE account — it cannot be automated or
scripted on your behalf, and there is no project-level shared credential.

You do **not** need to do any of this to develop or test `superfly` itself:
`MockDataSource` provides fully offline synthetic fixture data for that. Only
do this when you're ready to query the real dataset.

## 1. Register for CAVE Framework access

1. Go to the CAVE Framework auth portal and sign in (Google login is
   supported).
2. Request/accept access to the FlyWire FAFB production dataset. Approval may
   not be instant — it can require manual review on CAVE's side.

## 2. Generate an auth token

Once you have an account with dataset access, generate a token through
`caveclient`'s built-in auth flow:

```python
from caveclient import CAVEclient

client = CAVEclient()
client.auth.get_new_token()  # opens a browser flow / prints a URL to visit
client.auth.save_token(token="<paste the token shown after authenticating>")
```

This only needs to be run once per machine. `CAVEclient` handles the rest of
the token lifecycle (refresh, reuse) automatically afterward.

## 3. Where the token is stored

`caveclient` writes the token to:

```
~/.cloudvolume/secrets/cave-secret.json
```

This file is created with standard user-only file permissions by
`caveclient` itself — `superfly` never reads, writes, or otherwise touches
it directly. `FlyWireDataSource` simply constructs a `CAVEclient()` instance,
which picks the token up from this file automatically.

## 4. Never commit your token

- This file lives outside the repo (under your home directory), so normal
  `git add`/`git commit` usage won't pick it up.
- As a safety net, double-check `.gitignore` excludes any `*cave-secret*` or
  `*.cloudvolume*` paths before committing if you ever copy credentials
  somewhere inside the project directory for local experimentation — but the
  default setup above never requires doing so.
- If a token is ever accidentally exposed (e.g. committed, logged, or
  pasted somewhere public), revoke it from the CAVE auth portal and generate
  a new one immediately.

## 5. Verify it works

```python
from superfly.datasources.flybywire import FlyWireDataSource

ds = FlyWireDataSource()
ds.client  # raises AuthenticationError with a hint back to this doc on failure
```

If authentication fails, `FlyWireDataSource` raises `AuthenticationError`
with a message pointing back to this document.

## 6. If you get a 403 "missing_permission" error

A token that's valid but gets a `403 Client Error: FORBIDDEN ... missing
permission: view for dataset ...` means your CAVE account doesn't have `view`
access to the specific *datastack* `FlyWireDataSource` requested — having a
CAVE account/token and having per-dataset permissions are separate approval
steps. `FlyWireDataSource` defaults to the `flywire_fafb_public` datastack,
which is what most external accounts actually have access to; the restricted
`flywire_fafb_production` datastack requires separate approval and is not
the default here.

To find the exact valid datastack names (don't guess — they don't always
match the dataset names shown on the Codex token page), query CAVE's info
service directly:

```python
from caveclient import CAVEclient

client = CAVEclient()  # no datastack name needed for this call
print(client.info.get_datastacks())
```

Then pass the matching name explicitly if it isn't `flywire_fafb_public`:

```python
from superfly.datasources.flybywire import FlyWireDataSource

ds = FlyWireDataSource(dataset="flywire_fafb_public")  # or whatever you're granted
```

## 7. How region lookups work (and their caveats)

Unlike `cell_type` and `superclass`, which come straight from columns in the
hierarchical annotation table, **the annotation table has no region column
at all**. `load_region()` is instead derived from synapse-to-neuropil data:

1. Query the `valid_synapses_nt_np_v6` CAVE view for synapses whose assigned
   `neuropil` matches the requested region.
2. Count how many of those synapses each neuron participates in (as either
   the pre- or post-synaptic partner).
3. Keep neurons with at least `region_min_synapses` (default 5).
4. Join against the annotation table, which drops unproofread fragments —
   these make up a large share of raw synapse endpoints.

**This is approximate.** Large neuropils contain far more synapses than the
sampled `region_synapse_limit` (default 50,000), so the result is a *subset*
of the region's neurons, biased toward densely-connected ones. Both knobs are
tunable:

```python
ds = FlyWireDataSource(
    region_synapse_limit=200_000,  # better coverage, much slower
    region_min_synapses=20,        # stricter "is really in this region"
)
```

As a sanity check, `load_region("AL_R")` (the right antennal lobe, the fly's
primary olfactory center) returns a set dominated by `sensory` super-class
neurons with `ORN_*` (olfactory receptor neuron) cell types — biologically
what you'd expect.

Region names are **exact, case-sensitive CAVE neuropil names**, usually with
a side suffix: `AL_R`, `AL_L`, `MB_CA_R`, `LH_R`, `PLP_L`, plus unpaired
midline ones like `EB`, `FB`, `PB`, `GNG`. An unrecognized name raises
`RegionNotFoundError`. To list the valid names:

```python
from caveclient import CAVEclient

client = CAVEclient("flywire_fafb_public")
print(client.materialize.get_table_metadata("fly_synapses_neuropil_v6")["description"])
```

