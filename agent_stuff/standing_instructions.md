# User-Specific Standing Instructions

These are instructions that come from your persistent memory (`/memories/`), layered on top of the base agent instructions (which are assumed and not repeated here). Anything here supersedes or adds to the base behavior.

## Planning & execution preferences (`/memories/planning_preferences.md`)

### Chunked execution plans
- When breaking work into shots/waves/chunks, always break the plan into **phases first**, then **chunks within each phase**.
- Chunk numbering: use **dotted `{phase}.{local-chunk}` numbering** (e.g. `1.1`, `1.2`, `2.1`, `2.2`, `2.3`), not flat continuous numbering across the whole plan. Each phase's local chunk count resets to 1. This keeps each phase's branch commit history reading naturally from 1, keeps the number self-documenting (you can tell which phase a chunk belongs to without checking the Phase column), and limits renumbering blast radius to a single phase if chunks are inserted/reordered mid-flight.
- **Exception**: never renumber chunks that are already committed/merged — commit messages are immutable history once pushed. If a numbering scheme changes mid-plan, only apply it going forward to not-yet-executed chunks; leave completed chunks' historical numbers (and their literal commit messages) as-is in the checklist.
- The agent is responsible for producing the phase/chunk breakdown.
- The user is responsible for **manually configuring the model per chunk** to keep costs down. The agent may recommend a model and effort level from the approved pool, but the user's manual selection is authoritative.
- Use the approved model table below as the source of truth for available models and their stats.
- Do not introduce models outside the approved pool.
- Before **every chunk**, state the branch name for that chunk (see Git workflow below).
- At the **end of every chunk**, state: `Next: Chunk N — [brief description] — recommended: [model] — effort: [level] — context: [context window] — branch: [branch name] — commit: "[commit message]"`
- After the **final chunk**: state `All chunks complete.`
- **ALWAYS include the phase/chunk breakdown INSIDE the plan itself** — never present a plan without it.
- **Checklist upkeep**: immediately after finishing a chunk's actual work (files created/edited and verified), tick that chunk's row off (`[ ]` → `[x]`) in the plan's Checklist table. When a phase's PR is actually opened/merged (confirmed by the user), tick off that phase's PR row too. If in ask mode when a chunk finishes, note that the checklist is stale and tick it off as soon as back in an editing-capable mode — don't let completed work sit unchecked.
- **Single source of truth**: the plan file must also include a condensed tabular **Checklist** section (columns: Done, #, Phase, Chunk, Recommended, Effort, Context, Branch, Commit message, plus one row per phase for its PR) embedded directly in the same plan file, so it can be used as a dev checklist. Do **not** create a separate derived summary/checklist file elsewhere — one plan file holds both the detailed steps and the condensed checklist, to avoid drift between copies.

### Git workflow for chunked plans
- Naming convention: **Conventional Commits**, applied consistently to branch names, commit messages, and PR titles — the common modern standard (popularized via Angular/Google-affiliated tooling).
- Conventional Commit types in use: `feat` (new capability), `fix` (bug fix), `refactor` (restructuring, no behavior change), `test` (test-only changes), `docs` (documentation only), `chore` (tooling/config/scaffolding, no source behavior), `ci` (CI/CD configuration). Pick the type that best matches each chunk/phase's actual content.
- Branch: one branch per **phase**, named `{type}/{project-slug}-{phase-slug}` (e.g. `feat/superfly-datasources`) — scoped to the type of work and the project/feature, **not** the phase number. Phase numbers are plan-document bookkeeping (they get reused across unrelated future plans and can drift if phases are reordered), so they're deliberately excluded from the durable branch name. All chunks within a phase commit to that phase's branch.
- Commit: each **chunk** produces its own commit on the phase branch, with a message of the form `{type}(chunk-{phase}.{local-chunk}): {short imperative description}` (e.g. `feat(chunk-2.1): add DataSource abstract interface`). The dotted number resets per phase; see chunk numbering rule above. Already-committed chunks keep their original literal commit message text (immutable history) even if the numbering scheme later changes.
- PR: at the **end of every phase** (after its last chunk), supply PR text for the user to copy/paste — text only. **Never include phase or chunk numbers/labels in the PR title or body** — those are internal plan-bookkeeping artifacts that won't mean anything to a reviewer (or to an LLM reviewing the diff later) outside the context of the planning doc. Instead:
  - **Title**: Conventional Commit form, `{type}: {concise description of the actual change}` — describe what the PR does, not where it sits in a phase sequence.
  - **Body**: a detailed, bulleted description written to be useful to **both human reviewers and LLMs** reading the diff cold, without needing the plan doc for context. Cover, per logical area of change (not per chunk number):
    - What was added/changed and why (the actual capability or fix, not "chunk N adds X").
    - Key design decisions or tradeoffs worth flagging for review.
    - Validation/testing performed (what was run, what passed, any gotchas discovered).
  - The plan file (and its phase/chunk numbering) remains the agent's own bookkeeping — useful for tracking progress across a multi-step execution, but it should never leak into artifacts meant for other readers (commit messages already carry chunk numbers per the rule above since those are scoped to one PR's immutable history, but PR titles/bodies and the final summary to the user should read as if phases never existed).
- **The agent never runs git commit, git push, or any GitHub PR/issue-creation action itself, under any circumstances — including chunk-completion commits — unless the user explicitly directs it to run that specific command in that turn.** This supersedes any earlier "commit per chunk" framing: completing a chunk's file edits does **not** imply permission to commit it. Instead, after finishing a chunk's work, the agent supplies:
  - The exact `git add` + `git commit -m "..."` command text (for the user to run themselves), with a commit message written to be useful to both human reviewers and LLMs reading the history later (what changed and why, key decisions, validation performed) — not just a terse chunk label.
  - At phase end, PR title/body text per the format above (no phase/chunk numbers in PR-facing text).
  - The user alone decides if/when to actually stage, commit, push, or open the PR.

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
