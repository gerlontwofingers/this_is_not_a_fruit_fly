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
- Chunk 3: `superfly/datasources/base.py` — `DataSource(ABC)` with `get_annotations(name, annotation_type)` and `get_adjacency(neuron_ids, min_synapses)` returning plain DataFrames. — recommended: Claude Sonnet 5 — effort: medium — context: 1M — branch: `feat/superfly-datasources` — commit: `feat(chunk-3): add DataSource abstract interface`
- Chunk 4: `superfly/datasources/flywire.py` — `FlyWireDataSource` wraps `fafbseg.flywire.search_annotations` / `flywire.get_adjacency` + `CAVEclient`, raises `AuthenticationError` pointing at `docs/SETUP.md` on auth failure. — recommended: Claude Sonnet 5 — effort: high — context: 1M — branch: `feat/superfly-datasources` — commit: `feat(chunk-4): add FlyWireDataSource real data source`
- Chunk 5: `superfly/datasources/mock.py` — `MockDataSource` reads small synthetic fixtures (in-memory DataFrames) for annotations/adjacency, for tests and offline dev/play. — recommended: Claude Haiku 4.5 — effort: n/a — context: 200K — branch: `feat/superfly-datasources` — commit: `feat(chunk-5): add MockDataSource for offline/test use`
- Chunk 6: `superfly/cache.py` — disk-cache wrapper (hashlib-keyed pickle cache in `~/.cache/superfly/`) applied around `FlyWireDataSource` calls only (mock stays uncached). — recommended: Claude Sonnet 5 — effort: medium — context: 1M — branch: `feat/superfly-datasources` — commit: `feat(chunk-6): add disk cache wrapper for FlyWireDataSource`
- PR (end of Phase 2): Title: `feat: Phase 2 — data source abstraction`. Body: summarizes Chunks 3–6 — introduces the `DataSource` interface, a real `FlyWireDataSource` (fafbseg/CAVEclient-backed, with auth-error handling), an offline `MockDataSource` fixture-backed implementation, and a disk cache layer around the real source. Depends on Phase 1.

Phase 3 — Core `FlyBrain` graph object (*depends on Phase 2*)
Branch: `refactor/superfly-flybrain-core`
- Chunk 7: `superfly/brain.py` — refactor the draft class in one pass: constructor takes `datasource: DataSource | None = None` (defaults to cached `FlyWireDataSource`); collapse `load_region`/`load_cell_type`/`load_superclass` into a shared private `_load(query, annotation_type, min_synapses)`; extract `_build_adjacency(neuron_ids, adj_df)` from the draft's `_fetch_connectivity`, raising `EmptyGraphError` on no neurons found; keep export methods `to_pyg`/`to_networkx`/`to_numpy`/`mask` with guarded optional imports (clear ImportError pointing at extras install). — recommended: Claude Opus 5 — effort: high — context: 1M — branch: `refactor/superfly-flybrain-core` — commit: `refactor(chunk-7): refactor FlyBrain onto injected DataSource`
- PR (end of Phase 3): Title: `refactor: Phase 3 — core FlyBrain graph object`. Body: summarizes Chunk 7 — refactors the draft `FlyBrain` class to depend on the injected `DataSource` abstraction, consolidates the three `load_*` methods, extracts adjacency-building into a helper, and guards optional torch/networkx exports. Depends on Phase 2.

Phase 4 — Tests & CI (*depends on Phase 3*, parallel with Phase 5)
Branch: `test/superfly-tests-ci`
- Chunk 8: `tests/conftest.py` — fixtures: synthetic annotations DataFrame (~5-10 neurons), synthetic pre/post/syn_count adjacency DataFrame, a `MockDataSource` instance built from them. — recommended: Claude Haiku 4.5 — effort: n/a — context: 200K — branch: `test/superfly-tests-ci` — commit: `test(chunk-8): add pytest fixtures for mock brain data`
- Chunk 9: `tests/test_brain.py` — load via mock, assert adjacency shape/values, test each export method (`to_numpy`, `to_networkx`; guard `to_pyg` if torch absent), test `mask`. — recommended: Claude Sonnet 5 — effort: medium — context: 1M — branch: `test/superfly-tests-ci` — commit: `test(chunk-9): add FlyBrain load/export tests`
- Chunk 10: `tests/test_datasources.py` (`MockDataSource` contract test; `FlyWireDataSource` auth-error path via monkeypatched failing client) + `tests/test_cache.py` (hit/miss behavior with a fake slow function). — recommended: Claude Sonnet 5 — effort: medium — context: 1M — branch: `test/superfly-tests-ci` — commit: `test(chunk-10): add datasource and cache tests`
- Chunk 11: `.github/workflows/ci.yml` — `uv sync` + `pytest` on push/PR, Python 3.11+. — recommended: Claude Haiku 4.5 — effort: n/a — context: 200K — branch: `test/superfly-tests-ci` — commit: `ci(chunk-11): add CI workflow`
- PR (end of Phase 4): Title: `test: Phase 4 — tests & CI`. Body: summarizes Chunks 8–11 — adds mock-data pytest fixtures, offline tests for `FlyBrain` loading/exports, datasource/cache contract tests, and a GitHub Actions workflow running pytest on push/PR. Depends on Phase 3; can merge in parallel with Phase 5.

Phase 5 — Docs (*parallel with Phase 4, depends on Phase 3 for accurate API*)
Branch: `docs/superfly-docs`
- Chunk 12: `docs/SETUP.md` — register for FlyWire/CAVE access (Google login via CAVE Framework auth portal), generate a token via `caveclient.CAVEclient().auth` setup flow, where it's stored, reminder never to commit it. — recommended: Claude Haiku 4.5 — effort: n/a — context: 200K — branch: `docs/superfly-docs` — commit: `docs(chunk-12): add CAVE auth setup docs`
- Chunk 13: update root `README.md` — project description, install instructions (`pip install -e ".[flywire,torch,viz]"`), quickstart using `MockDataSource` for offline exploration. — recommended: Claude Haiku 4.5 — effort: n/a — context: 200K — branch: `docs/superfly-docs` — commit: `docs(chunk-13): update README with install and quickstart`
- PR (end of Phase 5): Title: `docs: Phase 5 — docs`. Body: summarizes Chunks 12–13 — adds `docs/SETUP.md` for CAVE/FlyWire token setup and updates the root `README.md` with install instructions and an offline `MockDataSource` quickstart. Depends on Phase 3; can merge in parallel with Phase 4.

At the end of each chunk during execution, state: `Next: Chunk N — [brief description] — recommended: [model] — effort: [level] — context: [context window] — branch: [branch name] — commit: "[commit message]"`. After Chunk 13: `All chunks complete.`

**Checklist** (condensed tabular form — tick off as chunks complete; this table is the single source of truth alongside the detailed steps above)

| Done | # | Phase | Chunk | Recommended | Effort | Context | Branch | Commit message |
|---|---|---|---|---|---|---|---|---|
| [ ] | 1 | 1 | pyproject.toml + package skeleton + extras | Sonnet 5 | medium | 1M | chore/superfly-scaffolding | chore(chunk-1): add pyproject.toml and src/superfly package skeleton |
| [ ] | 2 | 1 | .gitignore + exceptions.py | Haiku 4.5 | n/a | 200K | chore/superfly-scaffolding | chore(chunk-2): add .gitignore and exception hierarchy |
| [ ] | — | 1 | PR: "chore: Phase 1 — repo & packaging scaffolding" | — | — | — | chore/superfly-scaffolding | — |
| [ ] | 3 | 2 | datasources/base.py (ABC) | Sonnet 5 | medium | 1M | feat/superfly-datasources | feat(chunk-3): add DataSource abstract interface |
| [ ] | 4 | 2 | datasources/flywire.py (real, auth) | Sonnet 5 | high | 1M | feat/superfly-datasources | feat(chunk-4): add FlyWireDataSource real data source |
| [ ] | 5 | 2 | datasources/mock.py | Haiku 4.5 | n/a | 200K | feat/superfly-datasources | feat(chunk-5): add MockDataSource for offline/test use |
| [ ] | 6 | 2 | cache.py | Sonnet 5 | medium | 1M | feat/superfly-datasources | feat(chunk-6): add disk cache wrapper for FlyWireDataSource |
| [ ] | — | 2 | PR: "feat: Phase 2 — data source abstraction" | — | — | — | feat/superfly-datasources | — |
| [ ] | 7 | 3 | brain.py refactor (core API) | Opus 5 | high | 1M | refactor/superfly-flybrain-core | refactor(chunk-7): refactor FlyBrain onto injected DataSource |
| [ ] | — | 3 | PR: "refactor: Phase 3 — core FlyBrain graph object" | — | — | — | refactor/superfly-flybrain-core | — |
| [ ] | 8 | 4 | tests/conftest.py | Haiku 4.5 | n/a | 200K | test/superfly-tests-ci | test(chunk-8): add pytest fixtures for mock brain data |
| [ ] | 9 | 4 | tests/test_brain.py | Sonnet 5 | medium | 1M | test/superfly-tests-ci | test(chunk-9): add FlyBrain load/export tests |
| [ ] | 10 | 4 | test_datasources.py + test_cache.py | Sonnet 5 | medium | 1M | test/superfly-tests-ci | test(chunk-10): add datasource and cache tests |
| [ ] | 11 | 4 | CI workflow | Haiku 4.5 | n/a | 200K | test/superfly-tests-ci | ci(chunk-11): add CI workflow |
| [ ] | — | 4 | PR: "test: Phase 4 — tests & CI" | — | — | — | test/superfly-tests-ci | — |
| [ ] | 12 | 5 | docs/SETUP.md | Haiku 4.5 | n/a | 200K | docs/superfly-docs | docs(chunk-12): add CAVE auth setup docs |
| [ ] | 13 | 5 | README.md update | Haiku 4.5 | n/a | 200K | docs/superfly-docs | docs(chunk-13): update README with install and quickstart |
| [ ] | — | 5 | PR: "docs: Phase 5 — docs" | — | — | — | docs/superfly-docs | — |

**Relevant files**
- `pyproject.toml` — new, project metadata + optional dependency groups.
- `src/superfly/brain.py` — new, refactored `FlyBrain` (from user's draft class).
- `src/superfly/datasources/base.py`, `flywire.py`, `mock.py` — new, data-source abstraction.
- `src/superfly/cache.py` — new, disk cache wrapper.
- `src/superfly/exceptions.py` — new, custom exception types.
- `tests/conftest.py`, `tests/test_brain.py`, `tests/test_datasources.py`, `tests/test_cache.py` — new.
- `.github/workflows/ci.yml` — new.
- `docs/SETUP.md`, `README.md` — new/updated.

**Verification**
1. `uv run pytest -v` passes fully offline (no network calls) using `MockDataSource` fixtures.
2. Manually confirm `FlyBrain(datasource=MockDataSource(...)).load_region('AL_R').to_numpy()` returns a correctly shaped dense array in a quick REPL/script.
3. CI workflow green on a test push.
4. Confirm `.gitignore` excludes any file matching CAVE secret paths/patterns before first commit.

**Further Considerations**
1. Real CAVE token setup requires the user to actually register on the FlyWire/CAVE Framework portal (Google login) — this is a manual, out-of-band step Phase 5 will document but cannot automate. Recommend doing this whenever ready to test against real data; all Phase 1-4 work is fully testable without it.
2. Torch/PyG/networkx are made optional extras rather than hard deps, since the user only needs them for later PSO/Doom/optimizer experiments — keeps the base install lightweight ("as pure Python as possible"). Confirm this tradeoff is acceptable.
