---
name: bug-triage
description: "Repeatable Asana bug pipeline: fetch the task, analyse its description and attached media, scout the code read-only, produce an evidence-backed triage dossier, then reframe the task in place and add a tests subtask — with a captains-call gate whenever evidence is insufficient or expected results need a product ruling. Use whenever Vaidik shares an Asana task/bug link with debug intent — \"debug this\", \"need to understand this task\", \"triage this bug\", \"root-cause this\", \"what's going on with REF-xxxx\" — or asks to run /bug-triage, even if he doesn't say 'triage'. Also the entry point for hook/OpenClaw-triggered autonomous runs (--autonomous). Not for feature documentation from scratch (refrens-feature-docs) or broad multi-repo investigations without a task (scout)."
argument-hint: "<asana-task-link> [--autonomous] [--model M --effort E] [--reviewer k3]"
model: fable
effort: medium
disable-model-invocation: false
---

# Bug Triage

**On load — config banner.** Before any other output, echo exactly one compact banner reflecting resolved values, then proceed:
`⚙️ bug-triage — lane: <interactive|autonomous> · task: <REF-id or gid> · author: <resolved model effort> · scouts: sonnet medium · reviewer: <sol high|k3>`
(For a partial or validation slice, append `· stages 1–N` and omit banner fields for stages that won't run.)
`Options: --autonomous · --model --effort · --reviewer k3 | Gates ahead: captains-call? → changes-or-create → asana push (parent + tests subtask)`

Model/effort resolution follows the same rule as `refrens-feature-docs`: `--model`/`--effort` win; otherwise the frontmatter default (fable medium) applies on Claude Code, and on Codex report the real session model — never echo "fable" where it can't run.

You are triaging one Refrens bug from its Asana task. The product of this skill is **verified understanding pushed back to where engineers will read it**: a root-caused, review-gated task body plus a tests subtask. Two lanes share one spine:

- **Interactive** (default): full pipeline through the in-place Asana rewrite.
- **Autonomous** (`--autonomous`, hook-triggered, headless): read-only stages only; its single write is one dossier *comment* on the task. It never rewrites the description and never creates subtasks — those need a human in the loop.

**Resume rule:** at the start of any interactive run, check the task's comments for a prior bug-triage dossier (marker: a comment starting `🤖 bug-triage dossier`). If one exists and the task body hasn't materially changed since, reuse its evidence instead of re-scouting, and ask its listed captains-calls first. This is how an autonomous run hands off to you.

**Already-reframed tasks:** if the description is already in target shape (a structured reframe — Scope/Reference sections, verified code facts, explicit rulings), the run becomes a **verify pass**: still execute the spine (auditing the task's own `file:line` citations is the point), but treat the task's recorded rulings as settled, and at stage 6 offer targeted corrections to the existing body instead of a full rewrite — a task Vaidik already shaped should not be flattened and regenerated.

## The spine (stages 1–5, both lanes)

### 1 · Fetch the task

`GET /api/1.0/tasks/{gid}?opt_fields=name,notes,html_notes,attachments.name,attachments.download_url,custom_fields,memberships,permalink_url` — `attachments` alone returns only gids; the explicit sub-fields are required. `download_url`s carry a time-limited `e=` expiry — download media promptly after fetching, and re-fetch the task if a URL has gone stale. `ASANA_PAT` from `/Users/apple/Refrens/Andromeda-temp/.env` (`set -a; source …/.env; set +a`; never print the PAT). Also list comments (`GET /tasks/{gid}/stories`) — for the resume rule and for context the reporter added after filing. The task as written is the source of truth for *what was reported*, not for what is wrong; the distinction drives everything downstream.

### 2 · Analyse content + media

Split the description into **individually verifiable claims** — a task that reads as one bug often contains several (a filter bug and a display bug, say), and each claim gets its own verdict. Then inspect every attachment: download via the attachment's `download_url`, extract frames from recordings (`ffmpeg -i rec.mp4 -vf fps=1/2 frame_%02d.png`, into the scratchpad), and Read the frames. Media routinely settles what prose can't — which column the reporter means by "amount", what URL actually failed. Quote evidence (visible URLs, on-screen values), don't paraphrase it.

If ffmpeg is unavailable, fall back to a single thumbnail (`qlmanage -t rec.mp4 -o <dir>` on macOS), record the degradation in the dossier header and the manifest, and continue on description + code evidence — a claim only code can settle doesn't need the frames, but one that hinges on what the reporter saw becomes **unverified** without them.

### 3 · Scout (read-only)

Launch `scout-codepaths` (sonnet medium, read-only) — partition the claims by owning repo, one agent per repo, in parallel, max 2. Brief each with: the claims it owns, the media evidence, the repo root under `/Users/apple/Refrens/Andromeda-temp/`, and the required output contract — **pointers + verbatim `file:line` quotes, never paraphrase**, tracing symptom → mechanism → owning repo. Optionally add one `codex-scout` (→ GPT-5.6 Luna) alongside when cross-vendor recon seems likely to see something different; skip it for obviously single-repo bugs.

**Escalation:** if two scout rounds still haven't produced a confirmed mechanism, or the claims span more than two repos, stop grinding and offer the full `/scout` protocol instead — this skill's scout stage is sized for surgical bugs.

### 4 · Triage synthesis (root author)

Synthesize the dossier yourself — this is the judgment stage, not a delegation. Give every claim exactly one verdict:

- **confirmed** — mechanism traced to code with `file:line` evidence.
- **refuted** — the evidence disproves the claim as reported.
- **fork** — the fix requires choosing between behaviours (e.g. outstanding-view vs ledger-view). Code evidence cannot settle it; only a ruling can.
- **unverified** — the claim can't be confirmed or refuted from description + media + code.

Cosmetic drift in the task's own citations (an off-by-one line number, a moved file) doesn't change a verdict — correct it in the Evidence cell and move on. A discrepancy only matters when it would change the fix contract or the expected behaviour; then the claim is **unverified** (or a **fork**, if it exposes a decision).

Dossier structure (always this shape — it's what the comment, the rewrite, and the resume rule all consume):

```
# Bug-triage dossier — <REF-id> · <task title>
Task gid <gid> · triaged <date> · confirmed N / refuted N / forks N / unverified N
(one line noting any degradation, e.g. media frames unavailable)

## Claims
| # | Claim (verbatim-ish) | Verdict: confirmed / refuted / fork / unverified | Evidence |

## Root cause
| Symptom | Mechanism | Evidence (file:line) |
Owning repo(s). One paragraph of mechanism prose.

## Fix contract (proposed)
Numbered, minimal, following an existing in-repo pattern where one exists (name it).

## Coverage skeleton
Dimensions × cases the tests must span (the tests subtask grows from this).

## Out of scope
What this fix deliberately does not touch, and why.

## ⚑ Captains-calls (omit section if none)
Each fork/gap: the decision, the options with trade-offs, your recommendation.
```

### 5 · Captains-call gate (auto)

The gate fires iff the dossier contains any **fork** or **unverified** claim, or the task's expected results are self-contradictory. A ruling already recorded in the task body counts as settled, not a fork — don't re-litigate decisions Vaidik has written down. No triggers → pass straight through silently; the gate is earned by evidence, not ceremony.

- **Interactive:** put each call to Vaidik via AskUserQuestion — options, trade-offs, recommendation first. His rulings become locked contract: fold them into the fix contract and record them so the rewrite's "Why it's built this way" section carries them. Only then proceed.
- **Autonomous:** hard stop. Never guess a ruling, never draft on an unapproved contract — a confidently wrong rewrite is worse than no rewrite. Proceed to the autonomous close-out below with the ⚑ section intact.

## Interactive lane (stages 6–11)

### 6–9 · Refine, review, confirm

Invoke **`refrens-feature-docs`** in reframe mode, scoped to **task + tests** (surgical — no PRD/Handoff/Plan), passing: the task gid/link, the dossier as grounding, any captains-call rulings as settled decisions (so its team-talk resolves off), and the tests coverage skeleton. That skill owns drafting, its reader-effort pass (`reader-effort-editor`, fable medium, cold read), the doc var-check (`codex-reviewer` → GPT-5.6 Sol high; `kimi-reviewer` when `--reviewer k3`), and the changes-or-create gate. Don't duplicate its gates here — your job resumes when the user confirms the push.

The TESTS draft derives from the task contract per that skill's derivation rules; seed it from the dossier's coverage skeleton and keep the canonical format (`serana/docs/TESTS-payment-records.md`).

### 10 · Asana write — parent in place, tests as subtask (hard gate)

Both writes use `asana-create-task`'s verified mechanics: `md2asana.py` for rich text, REST (not MCP) for `html_notes`, read-back after every write.

1. **Archive the original description first** — the rewrite is destructive and Asana keeps no usable history, so nothing may overwrite the parent until the old body is safe. Search existing subtasks (`GET /tasks/{gid}/subtasks`) for one named `[Original] …`. Found → the task's pre-triage body is already preserved; skip (re-runs must not archive bug-triage's own output as if it were the original). Not found → `POST /tasks/{gid}/subtasks` with `name: "[Original] <REF-id> — description archive · <date>"`, `PUT` its `html_notes` with the stage-1 `html_notes` verbatim (it's already valid Asana XML — re-wrap in `<body>`, no conversion), read back, then mark the subtask complete so it doesn't sit in the open list as work.
2. **Parent:** `PUT /tasks/{gid}` with the reframed `html_notes` (+ title if changed). Fields, assignee, memberships, existing attachments stay untouched. Read back and verify. Never run this step unless step 1's read-back passed.
3. **Tests subtask:** search the same subtask list for one named `[Tests] …`. Found → update it in place (same in-place philosophy as the parent). Not found → `POST /tasks/{gid}/subtasks` with `name: "[Tests] <REF-id> — coverage & regression"`, then `PUT` its `html_notes` from the TESTS draft. Read back and verify.

**The invariant:** the original is archived before it's overwritten, and test cases must always be there. This stage is not done — and the run must not report success — until the archive, the parent, *and* the tests subtask all pass read-back. If any write fails, say so loudly and stop; never close the run on a partial push.

### 11 · Runtime manifest

Close with one line listing what actually ran, real models only, omitting skipped stages:
`Agents: author fable medium · scouts scout-codepaths(sonnet medium, 2) · captains-call <fired: N rulings|passed> · refine refrens-feature-docs(fable high) · reader-effort reader-effort-editor(fable medium) · var-check codex-reviewer(sol high) · asana archive+parent+tests-subtask ✓`

## Autonomous lane close-out

After stage 5 (whether or not the gate fired):

1. **Skeptic audit:** send the dossier to `scout-skeptic` (sonnet medium, read-only) — its brief is to refute: unsupported claims, stale evidence, overconfident recommendations. Apply its confirmed findings; downgrade anything it credibly challenges from "confirmed" to "unverified". There's no human watching, so the skeptic is the only check between a plausible-but-wrong dossier and Asana.
2. **Post the dossier** as one comment: `POST /tasks/{gid}/stories` with `html_text`, opening with the marker line `🤖 bug-triage dossier · <date> · confirmed N / refuted N / forks N / unverified N`, then the dossier (including ⚑ section when gated). This is the lane's only write.
3. **Notify** if the run was gated: Slack DM to Vaidik if a Slack tool is connected, otherwise rely on the ⚑ marker. State clearly in the comment that the run is blocked on the listed calls.
4. Report the manifest: `Agents: author <model> · scouts … · skeptic scout-skeptic(sonnet medium) · dossier-comment ✓ · <blocked ⚑ N calls|clean>`.

No description edits, no subtasks, no drafts pushed anywhere — the interactive resume picks those up.

## Hook setup (reference, on request)

An OpenClaw/webhook trigger on new Bugs-Tech tasks should invoke: `claude -p "/bug-triage <task-permalink> --autonomous"`. Idempotency comes free from the resume rule — a re-fired hook sees the existing dossier marker and refreshes only if the task body changed. Don't set this up unprompted; it's outward-facing configuration.

## Runtime notes

- **Codex:** no Agent registry — run the scout stage inline with the same output contract (`file:line` quotes), and let `refrens-feature-docs`' own Codex ladder handle reader-effort/var-check bindings. Skeptic falls back to a fresh one-shot reviewer with the refute brief; report the degradation in the manifest instead of borrowing Claude labels.
- **Asana MCP** may replace raw REST for reads when connected; writes involving `html_notes` always go through REST (the MCP validator rejects attribute-carrying tags).
- Never print the PAT. Scratchpad for frames/downloads, not the repo.
