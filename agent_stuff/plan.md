## Plan: superfly — FlyWire brain-graph toolkit scaffolding

Build a testable, cacheable foundation around the FlyBrain concept before any Doom/PSO experiments. Core idea: split network/auth-dependent data fetching (CAVEclient/fafbseg) from a pure in-memory graph object (`FlyBrain`), so FlyBrain can be built, tested, and exported (PyG/networkx/numpy/mask) entirely offline via a mock data source, while a real `FlyWireDataSource` handles live queries with disk caching.

**Decisions**
- Package manager: uv + pyproject.toml, src-layout, pure Python core with fafbseg/torch/networkx as optional extras (`pip install superfly[torch,viz]`).
- Import package name: `superfly`.
- CAVE credentials: no custom .env — rely on caveclient's own token flow (`CAVEclient` writes to `~/.cloudvolume/secrets/cave-secret.json`, standard file perms). User has no CAVE account yet; will need to register via the CAVE Framework auth portal (Google login supported) and generate a token — document this as a one-time manual step in `docs/SETUP.md`. Never commit secrets; add to `.gitignore`.
- Testability: introduce a `DataSource` abstract interface with two implementations — `FlyWireDataSource` (real, wraps fafbseg/CAVEclient) and `MockDataSource` (fixture-backed, offline). `FlyBrain` depends only on the interface, injected via constructor, defaulting to `FlyWireDataSource`.
- Add a disk cache layer (`superfly/cache.py`) wrapping expensive annotation/adjacency queries, keyed by query params + materialization version, since CAVE queries are slow/rate-limited.
- pytest + GitHub Actions CI, using `MockDataSource` fixtures — no live network calls in tests.

**Model pool note**: recommendations below use the approved pool from `agent_stuff/standing_instructions.md` (Claude Opus 5 — 1M context, Claude Sonnet 5 — 1M context, Claude Haiku 4.5 — 200K context, Claude Fable 5.1 — 1M context). You configure the actual model per chunk manually to control cost — these are recommendations only, not auto-applied.

**Git workflow note**: Conventional Commits convention applied consistently to branch names, commit messages, and PR titles. Branch: `{type}/superfly-{slug}` — scoped to work type + project/feature, deliberately excluding the phase number (phase numbers are plan bookkeeping, not durable branch identity). Commit: `{type}(chunk-{N}): {short description}`. PR title: `{type}: Phase {N} — {phase name}` (phase number belongs here, scoped to one PR/plan). Types: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `ci`. Text/guidance only — branches, commits, and PRs are never created automatically; all git actions require your explicit action/confirmation.

**Steps** (phases contain chunks; chunk numbering is continuous across the whole plan)

Phase 1 — Repo & packaging scaffolding (no deps on later phases)
Branch: `chore/superfly-scaffolding`
- Chunk 1: `pyproject.toml` (uv-managed), `src/superfly/__init__.py`, `src/superfly/py.typed`, optional dependency groups (`flywire`: fafbseg/caveclient, `torch`: torch/torch_geometric, `viz`: networkx; core deps pandas/numpy/scipy). — recommended: Claude Sonnet 5 — effort: medium — context: 1M — branch: `chore/superfly-scaffolding` — commit: `chore(chunk-1): add pyproject.toml and src/superfly package skeleton`
- Chunk 2: `.gitignore` (secrets, `__pycache__`, cache dirs, `.venv`) + `superfly/exceptions.py` (`SuperflyError`, `AuthenticationError`, `RegionNotFoundError`, `EmptyGraphError`). — recommended: Claude Haiku 4.5 — effort: n/a — context: 200K — branch: `chore/superfly-scaffolding` — commit: `chore(chunk-2): add .gitignore and exception hierarchy`
- PR (end of Phase 1): Title: `chore: Phase 1 — repo & packaging scaffolding`. Body: summarizes Chunks 1–2 — adds uv-managed `pyproject.toml` with optional dependency groups (`flywire`/`torch`/`viz`), `src/superfly` package skeleton, `.gitignore`, and the `exceptions.py` error hierarchy. No behavior yet; sets up the base for Phase 2.

Phase 2 — Data source abstraction (*depends on Phase 1*)
Branch: `feat/superfly-datasources`
- Chunk 2.1: `superfly/datasources/base.py` — `DataSource(ABC)` with `get_annotations(name, annotation_type)` and `get_adjacency(neuron_ids, min_synapses)` returning plain DataFrames. — recommended: Claude Sonnet 5 — effort: medium — context: 1M — branch: `feat/superfly-datasources` — commit: `feat(chunk-2.1): add DataSource abstract interface`
- Chunk 2.2: `superfly/datasources/flybywire.py` — `FlyWireDataSource` wraps `fafbseg.flywire.search_annotations` / `flywire.get_adjacency` + `CAVEclient`, raises `AuthenticationError` pointing at `docs/SETUP.md` on auth failure. — recommended: Claude Sonnet 5 — effort: high — context: 1M — branch: `feat/superfly-datasources` — commit: `feat(chunk-2.2): add FlyWireDataSource real data source`
- Chunk 2.3: `superfly/datasources/mock.py` — `MockDataSource` reads small synthetic fixtures (in-memory DataFrames) for annotations/adjacency, for tests and offline dev/play. — recommended: Claude Haiku 4.5 — effort: n/a — context: 200K — branch: `feat/superfly-datasources` — commit: `feat(chunk-2.3): add MockDataSource for offline/test use`
- Chunk 2.4: `superfly/cache.py` — disk-cache wrapper (hashlib-keyed pickle cache in `~/.cache/superfly/`) applied around `FlyWireDataSource` calls only (mock stays uncached). — recommended: Claude Sonnet 5 — effort: medium — context: 1M — branch: `feat/superfly-datasources` — commit: `feat(chunk-2.4): add disk cache wrapper for FlyWireDataSource`
- PR (end of Phase 2): Title: `feat: Phase 2 — data source abstraction`. Body: summarizes Chunks 2.1–2.4 — introduces the `DataSource` interface, a real `FlyWireDataSource` (fafbseg/CAVEclient-backed, with auth-error handling), an offline `MockDataSource` fixture-backed implementation, and a disk cache layer around the real source. Depends on Phase 1.

Phase 3 — Core `FlyBrain` graph object (*depends on Phase 2*)
Branch: `refactor/superfly-flybrain-core`
- Chunk 3.1: `superfly/brain.py` — refactor the draft class in one pass: constructor takes `datasource: DataSource | None = None` (defaults to cached `FlyWireDataSource`); collapse `load_region`/`load_cell_type`/`load_superclass` into a shared private `_load(query, annotation_type, min_synapses)`; extract `_build_adjacency(neuron_ids, adj_df)` from the draft's `_fetch_connectivity`, raising `EmptyGraphError` on no neurons found; keep export methods `to_pyg`/`to_networkx`/`to_numpy`/`mask` with guarded optional imports (clear ImportError pointing at extras install). — recommended: Claude Opus 5 — effort: high — context: 1M — branch: `refactor/superfly-flybrain-core` — commit: `refactor(chunk-3.1): refactor FlyBrain onto injected DataSource`
- PR (end of Phase 3): Title: `refactor: Phase 3 — core FlyBrain graph object`. Body: summarizes Chunk 3.1 — refactors the draft `FlyBrain` class to depend on the injected `DataSource` abstraction, consolidates the three `load_*` methods, extracts adjacency-building into a helper, and guards optional torch/networkx exports. Depends on Phase 2.

Phase 4 — Tests & CI (*depends on Phase 3*, parallel with Phase 5)
Branch: `test/superfly-tests-ci`
- Chunk 4.1: `tests/conftest.py` — fixtures: synthetic annotations DataFrame (~5-10 neurons), synthetic pre/post/syn_count adjacency DataFrame, a `MockDataSource` instance built from them. — recommended: Claude Haiku 4.5 — effort: n/a — context: 200K — branch: `test/superfly-tests-ci` — commit: `test(chunk-4.1): add pytest fixtures for mock brain data`
- Chunk 4.2: `tests/test_brain.py` — load via mock, assert adjacency shape/values, test each export method (`to_numpy`, `to_networkx`; guard `to_pyg` if torch absent), test `mask`. — recommended: Claude Sonnet 5 — effort: medium — context: 1M — branch: `test/superfly-tests-ci` — commit: `test(chunk-4.2): add FlyBrain load/export tests`
- Chunk 4.3: `tests/test_datasources.py` (`MockDataSource` contract test; `FlyWireDataSource` auth-error path via monkeypatched failing client) + `tests/test_cache.py` (hit/miss behavior with a fake slow function). — recommended: Claude Sonnet 5 — effort: medium — context: 1M — branch: `test/superfly-tests-ci` — commit: `test(chunk-4.3): add datasource and cache tests`
- Chunk 4.4: `.github/workflows/ci.yml` — `uv sync` + `pytest` on push/PR, Python 3.11+. — recommended: Claude Haiku 4.5 — effort: n/a — context: 200K — branch: `test/superfly-tests-ci` — commit: `ci(chunk-4.4): add CI workflow`
- PR (end of Phase 4): Title: `test: Phase 4 — tests & CI`. Body: summarizes Chunks 4.1–4.4 — adds mock-data pytest fixtures, offline tests for `FlyBrain` loading/exports, datasource/cache contract tests, and a GitHub Actions workflow running pytest on push/PR. Depends on Phase 3; can merge in parallel with Phase 5.

Phase 5 — Docs (*parallel with Phase 4, depends on Phase 3 for accurate API*)
Branch: `docs/superfly-docs`
- Chunk 5.1: `docs/SETUP.md` — register for FlyWire/CAVE access (Google login via CAVE Framework auth portal), generate a token via `caveclient.CAVEclient().auth` setup flow, where it's stored, reminder never to commit it. — recommended: Claude Haiku 4.5 — effort: n/a — context: 200K — branch: `docs/superfly-docs` — commit: `docs(chunk-5.1): add CAVE auth setup docs`
- Chunk 5.2: update root `README.md` — project description, install instructions (`pip install -e ".[flywire,torch,viz]"`), quickstart using `MockDataSource` for offline exploration. — recommended: Claude Haiku 4.5 — effort: n/a — context: 200K — branch: `docs/superfly-docs` — commit: `docs(chunk-5.2): update README with install and quickstart`
- PR (end of Phase 5): Title: `docs: Phase 5 — docs`. Body: summarizes Chunks 5.1–5.2 — adds `docs/SETUP.md` for CAVE/FlyWire token setup and updates the root `README.md` with install instructions and an offline `MockDataSource` quickstart. Depends on Phase 3; can merge in parallel with Phase 4.

Phase 6 — Real-data schema compatibility fixes (*found via live testing against a real CAVE account after Phase 5*)
Branch: `fix/superfly-real-data-schema`

Context: manual real-data testing (chunk 5.1 setup, verified working auth against the `flywire_fafb_public` datastack) surfaced that `FlyWireDataSource.get_annotations()` is fundamentally broken against the real API — it calls `fafbseg.flywire.search_annotations(name, annotation_type=annotation_type)`, but the installed `fafbseg`'s `search_annotations()` takes no `annotation_type` kwarg at all (it's a free-text/regex search across all annotation columns combined). Pulling the real hierarchical annotation table (139,248 neurons) also revealed a schema mismatch against `MockDataSource`'s fixture: real columns are `cell_type` (matches), `super_class` (mock uses `superclass` — underscore mismatch), and there is **no `region` column at all** (region/neuropil assignment isn't part of this hierarchical annotation table in the real schema — `load_region()` currently has no real-data equivalent).

- Chunk 6.1: Fix `superfly/datasources/flybywire.py` `get_annotations()` — stop passing the invalid `annotation_type` kwarg to `search_annotations()`; fetch the full/unfiltered annotation table and filter client-side by column, via an internal canonical-name → real-column-name map (`"cell_type": "cell_type"`, `"superclass": "super_class"`). For `annotation_type="region"`, raise a clear, explicit error (not a silent KeyError) explaining region-based loading isn't supported against real data yet, pointing to `MockDataSource` or `load_cell_type`/`load_superclass` as working alternatives in the meantime. — recommended: Claude Sonnet 5 — effort: medium — context: 1M — branch: `fix/superfly-real-data-schema` — commit: `fix(chunk-6.1): correct FlyWireDataSource.get_annotations for real fafbseg API`
- Chunk 6.2: Validate `get_adjacency()` the same way against the real API (only `get_annotations()` has been live-tested so far) — confirm `flywire.get_adjacency()`'s actual signature/kwargs match what's called, fix any further drift found. Add a small manual real-data smoke-test script (e.g. `scripts/smoke_test_real_data.py`, not part of the offline pytest suite since it needs live CAVE auth) exercising `get_annotations`/`get_adjacency`/a full `FlyBrain.load_cell_type(...)` round trip, to catch this class of bug earlier next time. — recommended: Claude Sonnet 5 — effort: medium — context: 1M — branch: `fix/superfly-real-data-schema` — commit: `fix(chunk-6.2): validate and fix FlyWireDataSource.get_adjacency against real API`
- Chunk 6.3 (exploratory/research): Investigate the correct real API for per-neuron region/neuropil assignment (likely synapse-level neuropil data via CAVE materialized tables, aggregated to a per-neuron "primary region" — e.g. the neuropil with the most synapses for that neuron) and implement real `load_region()` support if a clean path exists; document the aggregation method and any caveats/approximations in `docs/SETUP.md`. If no clean path is found, document that explicitly as a known limitation instead of a bug. — recommended: Claude Opus 5 — effort: high — context: 1M — branch: `fix/superfly-real-data-schema` — commit: `feat(chunk-6.3): add real neuropil-based region support to FlyWireDataSource` (or `docs(chunk-6.3): document load_region real-data limitation` if no implementation lands)
- Chunk 6.4: Add regression tests for the schema-mapping layer from 6.1 — a monkeypatched fake `fafbseg.flywire` module returning real-shaped columns (`cell_type`, `super_class`, no `region`) to assert `FlyWireDataSource` translates/filters correctly and raises the expected clear error for `region`. Keeps this bug class caught offline in CI going forward, without needing live CAVE auth. — recommended: Claude Sonnet 5 — effort: medium — context: 1M — branch: `fix/superfly-real-data-schema` — commit: `test(chunk-6.4): add schema-mapping regression tests for FlyWireDataSource`
- PR (end of Phase 6): Title: `fix: correct FlyWireDataSource against the real fafbseg/CAVE API`. Body: summarizes Chunks 6.1–6.4 — fixes the broken `get_annotations()` call signature, validates/fixes `get_adjacency()` against the real API, adds (or documents the absence of) real region/neuropil support, and adds offline regression tests for the schema-mapping layer. Depends on Phase 3; informed by live real-data testing done during Phase 5/6.

Phase 7 — Demo notebook (*depends on Phase 6 for an honest real-data story; mock-only parts could ship earlier*)
Branch: `docs/superfly-demo-notebook`
- Chunk 7.1: `demo.ipynb` at repo root — Part 1: offline `MockDataSource` walkthrough (load by region/cell_type/superclass, `to_numpy`/`to_networkx` exports, `mask()` demo). Part 2: real FlyWire walkthrough using `FlyWireDataSource` (`load_cell_type`/`load_superclass`, noting `load_region`'s real-data status per Phase 6), plus a disk-cache timing demo (first call slow, cached call fast). All real-data cells wrapped so the notebook still runs top-to-bottom for someone without CAVE auth configured (clear markdown callouts, not silent failures). — recommended: Claude Haiku 4.5 — effort: n/a — context: 200K — branch: `docs/superfly-demo-notebook` — commit: `docs(chunk-7.1): add demo notebook`
- PR (end of Phase 7): Title: `docs: add superfly demo notebook`. Body: summarizes Chunk 7.1 — adds a root-level `demo.ipynb` walking through offline mock usage, real FlyWire data usage, and disk-cache behavior. Depends on Phase 6 for accurate real-data behavior.

At the end of each chunk during execution, state: `Next: Chunk N — [brief description] — recommended: [model] — effort: [level] — context: [context window] — branch: [branch name] — commit: "[commit message]"`. After Chunk 7.1: `All chunks complete.`

**Chunk numbering note**: chunks 1 and 2 (Phase 1) keep their original flat numbers because they're already committed/merged — commit messages are immutable history. Chunk 2.1 onward uses dotted `{phase}.{local-chunk}` numbering (resets per phase) per the updated standing instructions.

**Checklist** (condensed tabular form — tick off as chunks complete; this table is the single source of truth alongside the detailed steps above)

| Done | # | Phase | Chunk | Recommended | Effort | Context | Branch | Commit message |
|---|---|---|---|---|---|---|---|---|
| [x] | 1 | 1 | pyproject.toml + package skeleton + extras | Sonnet 5 | medium | 1M | chore/superfly-scaffolding | chore(chunk-1): add pyproject.toml and src/superfly package skeleton |
| [x] | 2 | 1 | .gitignore + exceptions.py | Haiku 4.5 | n/a | 200K | chore/superfly-scaffolding | chore(chunk-2): add .gitignore and exception hierarchy |
| [x] | — | 1 | PR: "chore: Phase 1 — repo & packaging scaffolding" | — | — | — | chore/superfly-scaffolding | — |
| [x] | 2.1 | 2 | datasources/base.py (ABC) | Sonnet 5 | medium | 1M | feat/superfly-datasources | feat(chunk-2.1): add DataSource abstract interface |
| [x] | 2.2 | 2 | datasources/flybywire.py (real, auth) | Sonnet 5 | high | 1M | feat/superfly-datasources | feat(chunk-2.2): add FlyWireDataSource real data source |
| [x] | 2.3 | 2 | datasources/mock.py | Haiku 4.5 | n/a | 200K | feat/superfly-datasources | feat(chunk-2.3): add MockDataSource for offline/test use |
| [x] | 2.4 | 2 | cache.py | Sonnet 5 | medium | 1M | feat/superfly-datasources | feat(chunk-2.4): add disk cache wrapper for FlyWireDataSource |
| [ ] | — | 2 | PR: "feat: Phase 2 — data source abstraction" | — | — | — | feat/superfly-datasources | — |
| [x] | 3.1 | 3 | brain.py refactor (core API) | Opus 5 | high | 1M | refactor/superfly-flybrain-core | refactor(chunk-3.1): refactor FlyBrain onto injected DataSource |
| [ ] | — | 3 | PR: "refactor: Phase 3 — core FlyBrain graph object" | — | — | — | refactor/superfly-flybrain-core | — |
| [x] | 4.1 | 4 | tests/conftest.py | Haiku 4.5 | n/a | 200K | test/superfly-tests-ci | test(chunk-4.1): add pytest fixtures for mock brain data |
| [x] | 4.2 | 4 | tests/test_brain.py | Sonnet 5 | medium | 1M | test/superfly-tests-ci | test(chunk-4.2): add FlyBrain load/export tests |
| [x] | 4.3 | 4 | test_datasources.py + test_cache.py | Sonnet 5 | medium | 1M | test/superfly-tests-ci | test(chunk-4.3): add datasource and cache tests |
| [x] | 4.4 | 4 | CI workflow | Haiku 4.5 | n/a | 200K | test/superfly-tests-ci | ci(chunk-4.4): add CI workflow |
| [ ] | — | 4 | PR: "test: Phase 4 — tests & CI" | — | — | — | test/superfly-tests-ci | — |
| [x] | 5.1 | 5 | docs/SETUP.md | Haiku 4.5 | n/a | 200K | docs/superfly-docs | docs(chunk-5.1): add CAVE auth setup docs |
| [x] | 5.2 | 5 | README.md update | Haiku 4.5 | n/a | 200K | docs/superfly-docs | docs(chunk-5.2): update README with install and quickstart |
| [ ] | — | 5 | PR: "docs: Phase 5 — docs" | — | — | — | docs/superfly-docs | — |
| [x] | 6.1 | 6 | fix get_annotations() real API call | Sonnet 5 | medium | 1M | fix/superfly-real-data-schema | fix(chunk-6.1): correct FlyWireDataSource.get_annotations for real fafbseg API |
| [x] | 6.2 | 6 | validate/fix get_adjacency() + smoke test script | Sonnet 5 | medium | 1M | fix/superfly-real-data-schema | fix(chunk-6.2): validate and fix FlyWireDataSource.get_adjacency against real API |
| [x] | 6.3 | 6 | real region/neuropil support (research) | Opus 5 | high | 1M | fix/superfly-real-data-schema | feat(chunk-6.3): add real neuropil-based region support to FlyWireDataSource |
| [ ] | 6.4 | 6 | schema-mapping regression tests | Sonnet 5 | medium | 1M | fix/superfly-real-data-schema | test(chunk-6.4): add schema-mapping regression tests for FlyWireDataSource |
| [ ] | — | 6 | PR: "fix: correct FlyWireDataSource against the real fafbseg/CAVE API" | — | — | — | fix/superfly-real-data-schema | — |
| [ ] | 7.1 | 7 | demo.ipynb at repo root | Haiku 4.5 | n/a | 200K | docs/superfly-demo-notebook | docs(chunk-7.1): add demo notebook |
| [ ] | — | 7 | PR: "docs: add superfly demo notebook" | — | — | — | docs/superfly-demo-notebook | — |

**Relevant files**
- `pyproject.toml` — new, project metadata + optional dependency groups.
- `src/superfly/brain.py` — new, refactored `FlyBrain` (from user's draft class).
- `src/superfly/datasources/base.py`, `flybywire.py`, `mock.py` — new, data-source abstraction.
- `src/superfly/cache.py` — new, disk cache wrapper.
- `src/superfly/exceptions.py` — new, custom exception types.
- `tests/conftest.py`, `tests/test_brain.py`, `tests/test_datasources.py`, `tests/test_cache.py` — new.
- `.github/workflows/ci.yml` — new.
- `docs/SETUP.md`, `README.md` — new/updated.
- `src/superfly/datasources/flybywire.py` — fix (Phase 6): correct real API usage, schema mapping, region support/limitation.
- `scripts/smoke_test_real_data.py` — new (Phase 6): manual live-auth smoke test, not part of pytest.
- `demo.ipynb` — new (Phase 7): root-level demo notebook, mock + real data.

**Verification**
1. `uv run pytest -v` passes fully offline (no network calls) using `MockDataSource` fixtures.
2. Manually confirm `FlyBrain(datasource=MockDataSource(...)).load_region('AL_R').to_numpy()` returns a correctly shaped dense array in a quick REPL/script.
3. CI workflow green on a test push.
4. Confirm `.gitignore` excludes any file matching CAVE secret paths/patterns before first commit.

**Further Considerations**
1. Real CAVE token setup requires the user to actually register on the FlyWire/CAVE Framework portal (Google login) — this is a manual, out-of-band step Phase 5 will document but cannot automate. Recommend doing this whenever ready to test against real data; all Phase 1-4 work is fully testable without it.
2. Torch/PyG/networkx are made optional extras rather than hard deps, since the user only needs them for later PSO/Doom/optimizer experiments — keeps the base install lightweight ("as pure Python as possible"). Confirm this tradeoff is acceptable.
