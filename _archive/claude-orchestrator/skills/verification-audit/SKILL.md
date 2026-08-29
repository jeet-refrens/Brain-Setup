---
name: verification-audit
description: >-
  Read-only post-implementation verification audit: checks an implementation
  harness's verification bundle (proof-report + scenario artifacts) and the
  actual PR diffs against the feature's PRD/TESTS/HANDOFF acceptance criteria,
  and produces a corrected Scouting Dossier with a per-AC coverage table,
  ranked drift list, open-questions ledger, claimed-vs-proven list, and a
  readiness call. Use whenever Vaidik asks to audit, verify, or cross-check an
  implementation or verification bundle against the PRD / test cases /
  acceptance criteria / handoff — e.g. "audit this against our PRD", "verify
  the implementation output", "are there gaps or drifts vs the spec", "is this
  ready to merge against the acceptance criteria", "run a verification audit"
  — even if he doesn't say "audit". Not for pre-implementation scouting
  (/scout), bug triage (bug-triage), or writing the docs themselves
  (refrens-feature-docs).
argument-hint: "<bundle path, spec doc paths, task/PR links> [--model --effort --diff-lane codex|sonnet]"
model: opus
effort: high
---

# Verification Audit

**On load — config banner.** Before any other output, echo exactly one compact banner, then proceed:
`⚙️ verification-audit — navigator: <model effort> · diff lane: <codex-verifier gpt-5.6-terra medium | scout-codepaths sonnet> · skeptic: scout-skeptic (mandatory)`
`Options: --model --effort (navigator) · --diff-lane codex|sonnet · --scout-model --scout-effort | Artifacts: ~/.claude/scout-runs/<run> + repo mirror`

Act as the audit navigator. This is a specialization of the Scout protocol for one question: **does the evidence prove the implementation is faithful to the spec, and what exactly still stands between it and merge?** You hold the map, delegate evidence-heavy reading, adjudicate disagreements against raw sources yourself, and author the dossier. Defaults: Opus high navigator (configurable via `--model`/`--effort` — never silently substitute a rejected override), diff-verification lane on `codex-verifier` (GPT-5.6 Terra medium), skeptic always Claude.

Read-only throughout: never modify source repos, specs, the bundle, or PRs; never merge, deploy, or make state-changing production requests. The only writes are audit artifacts under the run directory and the repo mirror.

Inherit the Scout contracts — read `~/.claude/skills/scout/references/evidence-standard.md` and `scout-report-contract.md` before dispatching any lane, and follow the visibility contract in `~/.claude/agents/lib/visibility-contract.md`. The evidence standard binds the navigator's own inline analysis, not just scout reports.

## Inputs

Extract from the arguments (ask one high-leverage `AskUserQuestion` only if a missing item materially changes scope; otherwise proceed with labeled assumptions):

- **Verification bundle** — path or zip: `proof-report.md` (or equivalent) plus per-scenario folders (png/mp4/csv/traces).
- **Spec set (source of truth)** — the PRD, TESTS, and HANDOFF docs. These must carry numbered ACs/TCs/OQs/decisions (the refrens-feature-docs format); if they don't, say so and negotiate a claim list with the user before auditing.
- **Task / PR links** — the Asana task and any known PR URLs.

## Run directory

Create `$HOME/.claude/scout-runs/<YYYY-MM-DD>-<feature-slug>-verification-audit/` (numeric suffix if taken). Derive `<feature-slug>` from the spec doc filenames (e.g. `PRD-line-item-csv-export.md` → `line-item-csv-export`), not from the bundle path — bundle folders are often generically named:

```text
SCOUT_MAP.md                 # durable low-resolution state, updated every cycle
SCOUTING_DOSSIER.md          # the deliverable
reports/
  cycle-01-contracts.md      # AC/TC coverage lane
  cycle-01-codepaths.md      # mechanism lane
  cycle-01-skeptic.md
  cycle-02-*.md              # targeted follow-ups (typically PR-diff verification)
  <repo>-pr-<n>.diff         # saved diffs — the verification substrate
```

## Protocol

### 1. Locate the code FIRST — before any other conclusion

Resolve the PRs before auditing anything else: follow the task links, run `gh pr list`/`gh pr view`, ask the user if links are missing. Shorthand refs like `serana#4725` need an owner: resolve each repo's `owner/repo` from the local checkout's `git remote -v` before any `gh` call, and if a named repo has no local checkout or ambiguous remotes, ask once rather than guessing. Save every diff into `reports/` with `gh pr diff`. This step is first because a previous audit confirmed code absence across the entire local workspace and nearly shipped "nothing to merge" — while the code sat in two open PRs. A local workspace tells you nothing about what exists; **never conclude "code is absent" from local inspection alone.** The saved diffs, not the workspace, are the verification substrate for all mechanism claims.

### 2. Navigator direct checks (keep these — do not delegate)

These need vision or arithmetic the text lanes can't do:

- **Artifact arithmetic**: byte-precise row/column counts on bundle CSVs vs the report's claims (`awk`/`csvkit`, not eyeballing).
- **Media and timestamps**: view key screenshots; compare every artifact's mtime against the proof-report's own timestamp. Artifacts *newer* than the report usually mean post-report fixes the report text doesn't know about — the report is a snapshot, not the final state.
- **Bundle hygiene**: root-level strays, empty dirs, artifacts from the wrong dataset. Record as hygiene notes, not contradictions, unless they change a verdict.

Write initial findings into `SCOUT_MAP.md`: claims to verify, known facts, unknowns, suspected contradictions.

### 3. Cycle 1 — two lanes, launched concurrently in one message

- **Contracts lane** (`scout-contracts`, Sonnet): map every AC/TC/OQ to an evidence status from bundle + spec. Output: the coverage table skeleton.
- **Mechanism lane** — route by `--diff-lane` (default `codex`):
  - `codex` → `codex-verifier` agent. Give it: the saved diff paths as the ONLY permitted sources, feature context, and a numbered claim list distilled from the spec's decisions and ACs (dedup keys, routing, guards, fixes — mechanism claims, one testable assertion each).
  - `sonnet` → `scout-codepaths` with the same brief. Choose sonnet when the report must speak the spec's AC/TC vocabulary end-to-end or Codex is unavailable. Whichever agent takes this lane in cycle 1 also takes its cycle-2 follow-ups.

  When the bundle's own proof-report already disputes a claim (a self-flagged bug, a NOT VERIFIED marker), tag that claim **contested** in the brief and say what each side asserts — the lane is then adjudicating a disagreement, not doing first-pass verification, and its citation must discriminate between the two readings.

Each brief must state: run dir and exact report path, in-scope boundary, cycle number, the precise claims, and the scout-report-contract requirement. Scouts return compact memos, not pasted reports.

### 4. Draft dossier, then the mandatory skeptic pass

Draft `SCOUTING_DOSSIER.md` (structure below), then invoke `scout-skeptic` on it. **The skeptic is not optional in this skill, whatever the lane** — in the canonical run it flipped the verdict from "not mergeable" to "mergeable pending sign-off" by finding evidence the navigator missed. Its brief must explicitly include: re-check bundle-root files and artifact mtimes vs report timestamp; hunt for evidence of post-report fixes; verify the draft's citations independently; and flag any scout disagreement the draft adopted silently.

### 5. Cycle 2 — resolve by evidence, not by picking a scout

For every skeptic finding and every inter-scout disagreement, send the smallest discriminating follow-up to the best-placed lane (usually diff verification of the specific contested mechanism). A disagreement between scouts is resolved only by a source citation both readings must survive. Surface the disagreement and its resolution in the dossier — silently adopting one scout's verdict is a recorded process fault of this protocol.

### 6. Finalize

Two rules from past faults: publish **no underived counts** (every "N of M proven" needs a visible derivation), and if a draft conclusion was corrected, keep a **"Correction on record"** note at the top of the dossier rather than silently rewriting history — the user compares versions.

## Dossier contract

`SCOUTING_DOSSIER.md` sections, in order:

1. **Bottom line** — faithful or not, and the exact list standing between now and merge, each item tagged *code defect* / *decision needed* / *process step*.
2. **(a) Coverage table** — one row per AC/TC. Legend (define it in the dossier): **PROVEN-live** (UAT artifact) · **PROVEN-unit** (PR test) · **PROVEN-code** (confirmed in diff) · **PARTIAL** · **DECISION** (needs human). Include a sub-table for properties the live environment structurally could not exercise but a unit test covers.
3. **(b) Drift list** — ranked; each entry FIXED / NON-ISSUE / OUT-OF-SCOPE-WATCH / OPEN with the diff or artifact evidence. Record resolved non-drifts so they aren't re-raised.
4. **(c) Open-questions ledger** — every spec OQ: RESOLVED (with evidence) / OPEN (with stated default and stakes) / DECISION PENDING @user.
5. **(d) Claimed-done, actually-proven** — what remains asserted-only, and why (decision, out-of-boundary, needs production observation).
6. **(e) Readiness call** — mergeable or not, the numbered conditions, confidence, and material unknowns. State the audit boundary explicitly (CI status, deploy state, and production load behavior are outside it unless checked).
7. **Runtime manifest** — actual navigator model/effort, each lane's agent + model + what it did, skipped lanes with reasons, cycle count, and whether the skeptic materially changed the verdict.

## Repo mirror and finish

Mirror `SCOUTING_DOSSIER.md` into `<repo>/docs/scout/<run-slug>/` of the primary spec repo. If that mirror path already holds artifacts, a prior audit of this feature exists: read its dossier as an input at intake (your dossier must state what changed since it), and mirror under this run's own suffixed slug — never overwrite a prior run's mirrored artifacts, for the same reason corrections stay on record. Finish by returning: run directory, the bottom line verbatim, the decision items waiting on the user, and the runtime manifest. If a decision item is pending (a DECISION row or PENDING OQ), end there — recommending, not deciding; product rulings belong to the user.
