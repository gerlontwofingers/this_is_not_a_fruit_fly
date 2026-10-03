# User-Specific Standing Instructions

These are instructions that come from your persistent memory (`/memories/`), layered on top of the base agent instructions (which are assumed and not repeated here). Anything here supersedes or adds to the base behavior.

## Planning & execution preferences (`/memories/planning_preferences.md`)

### Chunked execution plans
- When breaking work into shots/waves/chunks, always break the plan into **phases first**, then **chunks within each phase**.
- The agent is responsible for producing the phase/chunk breakdown.
- The user is responsible for **manually configuring the model per chunk** to keep costs down. The agent may recommend a model and effort level from the approved pool, but the user's manual selection is authoritative.
- Use the approved model table below as the source of truth for available models and their stats.
- Do not introduce models outside the approved pool.
- Before **every chunk**, state the branch name for that chunk (see Git workflow below).
- At the **end of every chunk**, state: `Next: Chunk N — [brief description] — recommended: [model] — effort: [level] — context: [context window] — branch: [branch name] — commit: "[commit message]"`
- After the **final chunk**: state `All chunks complete.`
- **ALWAYS include the phase/chunk breakdown INSIDE the plan itself** — never present a plan without it.
- **Single source of truth**: the plan file must also include a condensed tabular **Checklist** section (columns: Done, #, Phase, Chunk, Recommended, Effort, Context, Branch, Commit message, plus one row per phase for its PR) embedded directly in the same plan file, so it can be used as a dev checklist. Do **not** create a separate derived summary/checklist file elsewhere — one plan file holds both the detailed steps and the condensed checklist, to avoid drift between copies.

### Git workflow for chunked plans
- Naming convention: **Conventional Commits**, applied consistently to branch names, commit messages, and PR titles — the common modern standard (popularized via Angular/Google-affiliated tooling).
- Conventional Commit types in use: `feat` (new capability), `fix` (bug fix), `refactor` (restructuring, no behavior change), `test` (test-only changes), `docs` (documentation only), `chore` (tooling/config/scaffolding, no source behavior), `ci` (CI/CD configuration). Pick the type that best matches each chunk/phase's actual content.
- Branch: one branch per **phase**, named `{type}/{project-slug}-{phase-slug}` (e.g. `feat/superfly-datasources`) — scoped to the type of work and the project/feature, **not** the phase number. Phase numbers are plan-document bookkeeping (they get reused across unrelated future plans and can drift if phases are reordered), so they're deliberately excluded from the durable branch name. All chunks within a phase commit to that phase's branch.
- Commit: each **chunk** produces its own commit on the phase branch, with a message of the form `{type}(chunk-{N}): {short imperative description}` (e.g. `feat(chunk-3): add DataSource abstract interface`). Chunk numbers are fine here since commits are scoped to one PR/plan and typically get squashed on merge.
- PR: at the **end of every phase** (after its last chunk), supply PR text — title in the form `{type}: Phase {N} — {phase name}`, plus a body summarizing the chunks/commits in that phase and any verification notes — text only. Phase numbers belong here (and in the plan's checklist), not in the branch name, since a PR/checklist is inherently scoped to a single plan's history.
- This is guidance/text output only: never auto-create branches, auto-commit, or auto-open PRs. Actual git actions (branch creation, commits, pushes, PR creation) require explicit user action/confirmation per operational safety rules.

### Approved model pool (GitHub Copilot, as of September 2026)

| Model | Context window | Max output | Thinking / effort | Price (input / output per MTok) | Best for |
|---|---|---|---|---|---|
| **Claude Opus 5** | 1M tokens | 128K tokens | Adaptive thinking on by default; effort: low / medium / high / xhigh / max; defaults to **high** | $5 / $25 | Architecture, deep debugging, novel reasoning chunks |
| **Claude Sonnet 5** | 1M tokens | 128K tokens | Adaptive thinking on by default; effort: low / medium / high / max; defaults to **high** | $2 / $10 | General coding, refactoring, multi-file wiring chunks |
| **Claude Haiku 4.5** | 200K tokens | 64K tokens | Extended thinking (manual, not adaptive); no effort levels | $1 / $5 | Fast, repetitive, or trivial chunks |
| **Claude Fable 5.1** | 1M tokens | 128K tokens | Adaptive thinking **always on** (cannot be disabled); effort: low / medium / high / xhigh / max; defaults to **high** | $10 / $50 | Occasional ceiling model when Opus 5 at high effort falls short |

**Notes:**
- Opus 5 and Sonnet 5 support **adaptive thinking**, which adjusts reasoning depth based on task complexity. Effort can also be set manually per request.
- Haiku 4.5 uses **manual extended thinking** rather than adaptive thinking. It does not support configurable effort levels.
- Fable 5.1’s thinking is **always on**. It is priced at double Opus 5. Reserve it for the rare chunk where Opus 5 at high effort genuinely falls short.
- Fable 5.1 cache reads are $0.25 per million tokens, which can reduce cost on cache-heavy agentic work.

### Quick mapping when recommending a chunk model
- **Deep reasoning / architecture**: Claude Opus 5
- **General coding / wiring**: Claude Sonnet 5
- **Fast / trivial tasks**: Claude Haiku 4.5
- **Absolute ceiling / rare hard chunk**: Claude Fable 5.1

## Other project-scoped memory (not applicable here)

`/memories/vox_romana_preferences.md` holds preferences for a different repo (`vox_romana`), including a Claude-only agent pool, thinking-effort settings, and a required Phase/Chunk + commit-per-chunk + PR-per-phase workflow. That file is scoped to that project and does not apply to this repo (`this_is_not_a_fruit_fly`); it's noted here only so you know it exists and isn't in force in this workspace.

## Notes for this repo (`this_is_not_a_fruit_fly`)
- Branch-per-phase / commit-per-chunk / PR-text-per-phase workflow (see Git workflow above) is adopted for this repo's chunked plans, independent of the vox_romana-specific memory note above.
- No other repo-specific or session-specific overrides recorded yet beyond the active `superfly` scaffolding plan (see `agent_stuff/plan.md`).
