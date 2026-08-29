---
name: refrens-feature-docs
description: "Produces a coherent Refrens feature doc set: PRD, TESTS with coverage matrix, concise Asana task draft, and Handoff decision log. Use when Jeet asks to document a feature, epic, or bug end-to-end; write a PRD or test cases; turn a discussion or prototype into task-ready docs; improve an existing Asana task; run /refrens-feature-docs; create the doc set; PRD this; or document this feature properly. Modes: all (default, no engineering Plan) | prd | tests | task | handoff | plan. A team-talk phase (Matchday-style problem refinement and confirmation before drafting) runs by default on fresh all/prd runs with no decisions.md/ADR trail and no existing PRD; skip with 'skip team-talk' or --no-team-talk, force with --team-talk. Pass --engg-plan to include the otherwise on-request Plan. Walks through review, cross-doc edits, and confirmed Asana creation. Replaces refrens-task-creator."
model: Fabel
effort: high
---

# Refrens Feature Docs

**On load — config banner.** If the invocation args contain `--model` or `--effort`, parse and strip them first and resolve the effective model/effort from those values. Otherwise, the fallback default is **runtime-specific, not a fixed string**: on Claude Code, it's the frontmatter default (fable high) — that frontmatter field is a Claude Code-only mechanism the harness reads to pick the model, so echoing "fable high" is only ever correct there. On Codex, there is no frontmatter-driven model selection — Codex cannot switch itself to Fable (it doesn't exist in that runtime), so the banner must report whichever real GPT model/profile this Codex session is already running under, never the literal string "fable". If that can't be introspected, say so plainly (e.g. `model: <unresolved — Codex session model>`) rather than fabricating a value. If a requested model/effort is unavailable in the runtime, say so in the banner — never claim an override applied when it didn't, and never silently substitute a rejected model/effort. Resolve `team-talk` as `on` when `--team-talk` is present or the user explicitly asks for Matchday-style problem refinement before drafting; as `off` when `--no-team-talk` is present or the user says "skip team-talk" (any phrasing to that effect); otherwise as `auto` — meaning the call is made after grounding: it turns **on** for a fresh `all`/`prd`/`task` run whose grounding finds no `docs/decisions.md`, no ADR trail, and no existing PRD (cold-start risk), and stays **off** everywhere else (reframe mode, subset modes over an existing set, post-matchday runs with residue). When `auto` resolves, announce the outcome in one line before proceeding. Before any other output, echo exactly one compact banner reflecting the *resolved* values, then proceed:
`⚙️ refrens-feature-docs — mode: <all|prd|tests|task|handoff|plan|reframe> · model: <resolved model effort> · team-talk: <on|off|auto> · reader-effort: <on|offered> · doc var-check: <on|offered>`
`Options: modes all·prd·tests·task·handoff·plan · --team-talk/--no-team-talk (or "skip team-talk") · --engg-plan · --model --effort · reframe <asana-link> | Hooks: team-talk refinement · prototype-uat screens/qa/report | Gates ahead: team-talk confirmation? → reader-effort pass → var-check findings → changes-or-create → asana push`

You are helping Vaidik (PM at Refrens, a B2B invoicing/accounting platform for Indian SMBs) produce a coherent documentation set for one feature. **Three readers, four documents (plus an on-request Plan), zero duplicated ownership** — every fact has exactly one home; the other docs reference or compress it.

## The document model

| Doc | File | Reader | Question it answers |
|---|---|---|---|
| **PRD** | `docs/PRD-<feature>.md` | Product + the engineer doing tech design | What problem, why, how it must behave, how we'll know it works |
| **Tests** | `docs/TESTS-<feature>.md` | Engineer/agent writing the suite | Which failing tests define done |
| **Asana task** | `docs/TASK-<feature>.md` (draft) → Asana | Engineer picking it up + reviewers | What to build, condensed and scannable |
| **Handoff** | `docs/HANDOFF-<feature>.md` | Engineer/agent who wasn't in the room | Why it's shaped this way, what not to undo |
| **Plan** (on request only) | `docs/PLAN-<feature>.md` | Coding agent on the prototype | Exactly what to change, where, in what order |

**Derivation rules:** the PRD is written first and is the source of truth. The task is *derived* from it (compressed, never forked — if the task needs a fact the PRD lacks, fix the PRD first). The Tests doc derives from the PRD's ACs/FLs/ECs and the task's Reference contracts — if a test needs a fact neither doc has, fix the owner doc first, then write the test. The handoff *accumulates* append-only as decisions land. The Plan is **not part of the default set**: produce it only when explicitly requested (`plan` mode, `--engg-plan`, or a later "add the engg plan" on top of an existing set) and only for prototype/agent execution — an engineer working against prod code plans from their own scoping, not our prototype-era snapshot.

**Canonical examples** (match their structure, density, and language):
`/Users/apple/Refrens/Andromeda-temp/Document Formats/docs/v2/` — `PRD-document-formats.md`, `TASK-document-formats.md`, `HANDOFF-document-formats.md`, `PLAN-df-p1.md`.
For the Tests doc: `/Users/apple/Refrens/Andromeda-temp/serana/docs/TESTS-payment-records.md`.

## Modes

Parse the invocation args: `all` (default) · `prd` · `tests` · `task` · `handoff` · `plan` · `--team-talk` · `--no-team-talk` · `--engg-plan` · `--model` · `--effort`. Team-talk is a cross-cutting phase, not a mode: it runs after grounding and before drafting, then continues into the selected mode after the user confirms the sharpened problem. `--team-talk` forces it on; `--no-team-talk` (or the user saying "skip team-talk") forces it off; with neither, the `auto` rule from the banner section decides — on for cold starts (no decisions.md, no ADRs, no existing PRD), off when residue or an existing set makes the premise already established. `all` produces PRD + Tests + Task + Handoff — **no Plan** unless `--engg-plan` is passed or the user asks for it later. `--no-engg-plan` is retired; if it appears, accept it silently as a no-op (it now describes the default). When producing a subset, still check the siblings exist and offer to create/update the missing ones — but never treat a missing Plan as a gap to offer. Docs live in the feature's repo/folder under `docs/` (follow the repo's existing convention if one exists).

Example: `/refrens-feature-docs all --team-talk` grounds the feature, refines and confirms the problem, records the decisions, then produces the default four-document set.

**Reframing an existing Asana task** (user shares a task link/gid and asks to improve/restructure/verify it): fetch the current task first (`GET /api/1.0/tasks/{gid}?opt_fields=notes,html_notes` — PAT in `/Users/apple/Refrens/Andromeda-temp/.env`), treat its content as the raw input, verify every claim against the prototype/repo before rewriting, and surface spec-vs-prototype divergences in the task's "Why it's built this way" section rather than silently correcting the author's intent. Then proceed as normal: PRD first if none exists, task derived from it. Pushing the reframed task back updates the existing task (via `asana-create-task`'s rich-text mechanics with `PUT` instead of create) — confirm before overwriting.

## Workflow

1. **Ground first.** Read the feature folder (prototype code, existing docs, ADRs, CONTEXT.md, memories) and any linked Asana task before writing. Verify claims against code — never infer prototype behavior.

   *Grounding economics:* the residue docs (decisions.md, ADRs, CONTEXT.md, TEST-CASES) are pre-compressed by design — read them raw yourself, always; they're small and they're the truth. Delegate only **navigation**: when the repo is large or the residue is thin, send one subagent (Agent tool, `subagent_type: "Explore"`, Sonnet) to map which files matter — its output contract is *pointers and verbatim quotes with `file:line`, never paraphrased contracts*. Anything destined for a normative table, Reference section, or acceptance criterion comes from your own read of the cited lines. An author writing contracts from a scout's paraphrase is how confident-but-wrong PRDs happen.

   **This is not the `scout` skill.** This skill never invokes `scout`/`scout-navigator` — that's a full evidence-first investigation protocol (navigator + multiple scout lanes + adversarial skeptic pass + dossier), scoped for open-ended production/history investigations, not for pointing at files inside a feature folder you're about to write docs for. If the grounding question is genuinely that open-ended (e.g. reframing a task against unfamiliar production behavior), that's a signal to run `/scout` *before* this skill and feed its dossier in as residue — not to reach for it mid-skill.

   **The prototyping phase (matchday runs) leaves residue that is first-class input, not ambient context:** `docs/decisions.md` (the per-gate decision log matchday appends to) seeds the Handoff's decision journey — its D-entries become journey turns, with reversals preserved as supersessions; `docs/adr/` supplies the decided/locked constraints; `CONTEXT.md` fixes terminology (use its canonical terms verbatim); `plans/`/todo files reveal deferred scope for the PRD's Out list. Reconstruct from chat memory only what these files don't already record.
2. **Refine the problem when team-talk resolved on** (forced via `--team-talk`, or `auto` firing on a cold start — see Modes). Run the Team-Talk contract below and stop at its confirmation gate. After confirmation and decision capture, continue directly into this skill's clarification and drafting steps — do not enter Matchday's `tactics-board`, implementation, or release stages.
3. **Clarify** anything the conversation/prototype doesn't answer (see the clarification ladder below) — never write a new PRD cold. Team-Talk does not suppress later contract-level clarification if drafting exposes a new ambiguity.
4. **Draft** the docs per the templates below, running the quality gates. When the prototype is runnable, invoke the **`prototype-uat`** skill in `screens` mode to capture the captioned flow screenshots the task's Tutorial/scenario sections embed (they land in `docs/uat-assets/`); offer its `qa`/`report` modes when the user wants the Tests doc backed by executed evidence rather than just a mapping.
5. **Reader-effort pass** (see the section below): after the quality gates pass, send the drafted docs to the `reader-effort-editor` agent for an independent editorial review. Apply its SAFE EDITORIAL findings through the edit loop (announced in one summary line, never silently); hold its AUTHOR DECISION findings for the presentation step. Same default rule as the var-check: on when the doc set is engineering-bound, offered otherwise.
6. **Doc var-check** (see the section below): runs on the post-editorial bytes. Run it by default when the doc set is engineering-bound (about to be pushed to Asana for a sprint); offer it for smaller doc work. Skip only if the user declines.
7. **Present** a short summary of each doc (what it covers, what's open) plus the reader-effort AUTHOR DECISION items and var-check findings when those passes ran, then a **runtime manifest** line listing every agent actually invoked this run with its real model/effort — e.g. on Claude Code, `Agents: author fable medium · grounding Explore(sonnet, 1 call) · team-talk grill-with-docs(inherits session) · reader-effort reader-effort-editor(fable medium) · var-check codex-reviewer(sol high) · uat prototype-uat(inherits session)`; on Codex, `Agents: author <actual root model/effort> · reader-effort reader-effort-editor(gpt-5.6-sol xhigh) · var-check gpt-5.6-sol(high)` — omitting any step that didn't run rather than padding the line. Then **ask the user**: *make changes, or create the task in Asana?* (Use AskUserQuestion with those two options.)
8. **If changes:** edit conversationally — see *The edit loop* below.
9. **If create:** invoke the **`asana-create-task`** skill, passing: the task draft path, the companion doc paths to attach, the task type (feature/enhancement vs bug — ask if ambiguous), and the prototype URL + screenshot locations if a prototype exists.

## Team-Talk problem refinement

Reuse Matchday's problem-refinement contract without invoking the rest of Matchday:

1. Invoke **`grill-with-docs`** after grounding. Interview the user one question at a time.
2. Look up facts in the repo and residue instead of asking the user; put product and domain decisions to the user explicitly.
3. Restate the sharpened problem statement, including the affected user, current pain, desired outcome, scope boundary, and unresolved assumptions. Stop and ask the user to confirm or revise it. This confirmation is a hard gate; do not draft documents before it resolves.
4. After confirmation, append each resolved decision to `docs/decisions.md` using `### D<n> — <title> (<date>)` with **Context** / **Options** / **Decision** / **Why & trade-off** / **Refs**. Create the file if needed. Capture rejected options. Keep the log append-only; record reversals as new superseding entries. Use an ADR as well when `grill-with-docs` identifies a hard-to-reverse, surprising decision with a real trade-off.
5. Continue with this skill's normal clarification and document workflow. Treat the confirmed problem and decision entries as source residue for the PRD and Handoff, not as a separate authoritative document.

Scope boundary with `grill-with-docs` in the ladder: team-talk **establishes the premise** (problem, user, outcome, scope) before drafting; the ladder's Grill step **stress-tests a formed contract** when drafting hits deep ambiguity — one doesn't replace the other. When team-talk resolved off (skipped, or residue made it unnecessary), keep the existing behavior: ground first, then use the clarification ladder only as ambiguity appears. When forced via `--team-talk`, run it even when the initial problem already looks well-defined — and even in reframe/subset runs. A skip ("skip team-talk" / `--no-team-talk`) is always honored without argument, even on a cold start. Team-talk never authorizes Matchday planning, implementation, review, or release.

## The edit loop (after presenting)

Make requested changes as **inline edits to the live files**, conversationally — not by regenerating whole docs. After every edit, run the **dependency check**: a change rarely belongs to one doc.

- Ask yourself: *which doc OWNS this fact?* Edit the owner first, then propagate the compressed/reference forms. A user asking to change something in the **task** usually means the **PRD** contract changed → update the PRD (owner), then the task's compression of it, then check whether the Plan's work items or the Handoff's decisions shift.
- A scope change → PRD Scope + task Scope + Plan out-of-scope + possibly a new Handoff decision entry.
- A resolved open question → remove from PRD/task Open Questions, add a decision turn (D*n*) to the Handoff journey + matrix.
- A behavioral rule change → PRD flow/table (owner) + task flow + the Tests doc's TC groups and coverage matrix.
- A scope retirement → strike the affected TC group in the Tests doc (with reason) and sweep every doc for the retired ids — a cascade isn't done until a search for the superseded term across the whole set comes back clean.
- Say what you propagated and why, in one line per doc — don't silently multi-edit.

## PRD template

```
# <Feature> — PRD
status/owner/links table (Asana, prototype, companions)
"How to read this doc" note  ← OPTIONAL, only when needed: a glossary fixing each term that
                        has a near-synonym in the doc to ONE meaning, plus the doc-set
                        division of labor stated ONCE — after this note, never write
                        "X is covered in the Plan/Task" again anywhere in the doc
## What we're building ← 2–4 plain sentences stating the solution up front; never bury it
## Problem            ← prose, concrete, NO solution words (no component/schema/repo names)
## Why it matters     ← business value: frequency, compliance/error cost, retention/monetization, what it unlocks
## Acceptance criteria ← 4–7 checkable user-visible outcomes, as checkboxes
## Desired behavior   ← numbered flows FL1…FLn, functional language, incl. negative flows
                        ("user who ignores the feature sees no change"). Normative rules
                        (precedence orders, fallbacks, decision tables) go INLINE in the flow
                        that owns them, marked "(normative)".
## Scope              ← In (phase table if phased) / Out (deferred, named)
## Edge cases & break risks ← EC1…ECn; each either handled (which flow covers it) or
                        consciously accepted with the stated reason. Include "what existing
                        behavior could this break".
## What to test       ← a POINTER, not the list: state the convention ("every FL implies its
                        failure-mode tests") and link the TESTS doc as normative — the test
                        cases themselves live there, never inline here.
## Technical design (brief) ← MAX ~15% of the doc: chosen approach (a paragraph), rejected
                        alternatives (one line each + why), key insights, standing constraints.
                        Link deeper docs; never inline them.
## Open questions     ← each with owner (@person) and a stated working default
```

**The TDD gate (the PRD's reason to exist):** an engineer must be able to brainstorm a full tech design + test cases from this PRD alone (step 4 of the eng workflow). Before presenting, check every AC, FL rule, and EC: *could a stranger write a failing test for this without asking a question?* Unquantified adjectives ("meaningfully differs", "non-nagging", "fast") fail the gate unless the PRD defines them — turn them into decision tables, numbered precedence rules, or explicit thresholds. When a boundary is delegated to a linked table (e.g. a field-scope classification), say the link is **normative**.

## Tests template

```
# <Feature> — Test Cases
links (PRD, task, handoff) + the convention line ("every FL implies its failure-mode tests")

## Test groups           ← grouped by theme (Group A, B, …), each test a stable TC-id
                           (TC-A1, TC-B3 …) with: setup, action, expected result. Every
                           assertion grounded in a PRD AC/FL/EC id or a task Reference
                           contract — never in what "should" happen.
## Coverage matrix       ← REQUIRED, bidirectional: every AC/EC/FL row maps to ≥1 TC-id,
                           and every TC-id maps back to the AC/EC/FL it verifies. An
                           orphan in either direction fails the gate — a requirement with
                           no test, or a test verifying nothing named.
## What mocks can't verify ← name the assertions the suite CANNOT prove (env-dependent
                           behavior, cross-service state, live data invariants) and the
                           live assertion / manual check that covers each. Omit if none.
```

TC-ids are stable once minted — retire a group (strikethrough + reason), never renumber. When a decision changes scope (e.g. a method drops out of scope), sweep the whole doc for the retired tests' ids and update the coverage matrix in the same edit.

## Task template (Diataxis-shaped, framework unnamed)

```
# [type] <Feature title>
## Summary                    ← pain-led, 2–4 sentences prose, ends bold "After this ships, …"
## Scope                      ← in/out at a glance (phases if an epic)
## User Stories               ← 3–6; include one accuracy/consistency story
## Why it's built this way    ← decisions compressed to one line each + prototype-alignment
                                notes (where prototype lags spec, spec wins — say so)
## The primary flow           ← ONE persona-named end-to-end walkthrough, Step 1/2/3,
                                field tables, screenshot embeds where the prototype has them
## Other scenarios            ← one short recipe per secondary path; omit if none
## Reference                  ← exact contracts: schema/field tables, entry points + visibility
                                rules, server-derived values the client can't override, quota
                                tiers, enums, JV notation + status lifecycles for accounting features
## Test Edge Cases            ← grouped by theme; reference PRD EC ids and TESTS TC-ids
## Handling                   ← existing-data question @eng-lead, risks, open items, companion docs
```

Nothing appears here that isn't in the PRD, **except** Reference-mode contracts (field tables, JV entries, lifecycles) — those are task-level detail and live here, not in the PRD.

## Handoff template

```
# <Feature> — Handoff & Decision Log
audience / links / TL;DR (flag hard-won reversals up front)
## Decision matrix       ← table: D# | decision | status (decided / superseded-by / OPEN @owner) | ref
## Decision journey — READ THIS FIRST
                         ← chronological T1…Tn: the question, options, choice, why, rejected
                           paths, "do not reintroduce" warnings. Preserve REVERSALS explicitly
                           (what was superseded and why). Append-only; supersede, never edit.
## Code map & what already works ← repo/file table with state; "do not rebuild" list;
                           verified preconditions (assumptions checked in code, file:line)
## Pitfalls / do not undo
## Open questions        ← mirrors PRD's; this copy is the live one
## Changelog             ← dated one-liners as the docs/decisions evolve
```

## Plan template (on explicit request only — prototype/agent execution)

```
# Plan: [<phase-id>] <slice title>
goal + links (Asana child task, handoff, PRD flows it implements)
> staleness note when line numbers came from a scoping-time read
## Acceptance criteria (this slice)   ← checkboxes, up front
## Locked decisions this plan depends on ← one-liners pointing at the handoff; don't re-litigate
## Current code facts (verified)      ← real paths + line refs; where prototype lags spec, say tests define done
## Work by repo                       ← exact files, hooks, and surfaces to touch
## Test approach                      ← survey the test infrastructure that EXISTS (harnesses,
                                        conventions); layers (unit/integration/regression);
                                        name the regression suite that is the release gate
## Out of scope / Open items (checkboxes, each with when-it-must-resolve) / Implementation order
## Verification checklist             ← behavioral, checkbox form
```

## Writing conventions

- Clear, direct, engineering-readable prose. No fluff, no marketing language, no filler sections — **omit rather than write "None"**.
- **Bold** for UI elements, field names, statuses, action labels · `code` for enums, keys, endpoints, IDs · ~~strikethrough~~ for visible-but-out-of-scope UI.
- Field tables: **Field | Behaviour** (`Pre-filled, read-only` · `Editable — [constraint]` · `Required` · `Optional` · `Dropdown: […]`).
- JV entries (accounting features): debit first, credit indented with "To", labeled cases, Voucher Book Type/Name specified.
- Status lifecycles as code blocks with arrows; `[Future]` markers.
- IDs everywhere they buy traceability: FL/EC in the PRD, TC in the Tests doc, D/T in the handoff, referenced from task tests. Keep the scheme light.
- Every code fact carries `file:line`; every prototype claim is read from source.

## Quality gates (run before presenting)

1. **TDD gate** — see PRD template. This is the single most important gate.
2. **Simplicity gate** — strictest on the PRD and Tests doc: the PRD is the PM's core deliverable and must be a breeze to read. Principle: *writing in a difficult language is easy; writing in a simple language is the hardest.* Mechanical checks:
   - No rule or division-of-labor statement appears more than once in the doc — state it once (the "How to read this doc" note), then never re-explain or re-deflect ("X is covered in the Plan" twelve times is a bug, not thoroughness).
   - No sentence carries more than one qualification — split em-dash clause-stacks into one-claim sentences.
   - Plain word over Latinate when one exists: create not materialize, apply not instantiate, hand-written not bespoke, use not leverage.
   - Every term with a near-synonym elsewhere in the doc (registry/factory/adapter/facade…) is glossary-defined once and used only in that meaning.
   - The solution is stated plainly up front ("What we're building") — never buried mid-doc.
   - Bold only on load-bearing verdicts, not decoration. "Open Questions" contains only open items — decided ones move to the Handoff journey.
3. Problem/Why sections contain no solution words.
4. Technical design ≤ ~15% of the PRD; if it outgrows that, it's telling you the feature needs a separate engineering design doc — link it.
5. No fact stated twice across the set in owner form (compression/reference is fine; a second authoritative statement is a bug).
6. Every EC is mapped to a flow/test or consciously accepted with a reason — no orphans; the Tests doc's coverage matrix is bidirectional and complete (see Tests template).
7. Reversed decisions appear as supersessions in the handoff, never silently rewritten.

## Reader-effort pass (independent editorial review, before var-check)

One fresh-context editorial reviewer between drafting and the var-check. Its runtime binding is explicit:

- **Claude Code:** use the `reader-effort-editor` agent (Agent tool, `subagent_type: "reader-effort-editor"` — fable medium, read-only).
- **Codex:** use the custom `reader-effort-editor` agent from `~/.codex/agents/reader-effort-editor.toml` — `gpt-5.6-sol` at `xhigh` (**Extra High**), read-only. If named custom-agent selection is unavailable but native spawning exposes model and reasoning controls, spawn a fresh worker with `fork_turns: "none"`, model `gpt-5.6-sol`, and reasoning effort `xhigh`; instruct it to read `~/.codex/skills/reader-effort-editor/SKILL.md` completely before reviewing. Never use a full-history fork for this pass.

Its brief is reader effort, not correctness: orientation, sequencing, findability, working memory, density, terminology, format choice — the friction the author can't see from inside the draft. Same-vendor is deliberate and fine here: this pass's independence comes from the cold read (the agent carries none of the drafting conversation), not from vendor diversity; cross-vendor scrutiny is the var-check's job. The Claude agent file owns the shared editorial doctrine; the Codex skill is a thin runtime adapter over that same contract.

**Pass it:** the paths of every doc drafted or substantially rewritten this run (the whole set — cross-doc jump-chasing is in its scope), the intended reader for any non-default doc, the residue paths (decisions.md, ADRs, CONTEXT.md) for terminology canon, and a pointer to this skill's templates as the locked structural baseline — it must not flag template-mandated section order as friction.

**Handle its report:**
- **SAFE EDITORIAL** findings: apply through the edit loop (dependency check included) *before* the var-check, announced as one summary line — never silently.
- **AUTHOR DECISION** findings: leave the text untouched; surface them verbatim to the user alongside the var-check findings at the changes-or-create gate. The user, not the author, owns meaning choices.
- **Items for the correctness reviewer**: fold into the var-check brief.
- The verdict is advisory — single pass, no apply-and-re-run loop; re-run only if the user asks after major edits.

**Sequencing rule:** the var-check always runs on the post-editorial bytes, so applied editorial fixes get correctness scrutiny too.

## Doc var-check (independent adversarial review of the doc set)

One independent cross-vendor reviewer — the author model reviewing its own draft is not a second opinion. On Claude Code: the `codex-reviewer` agent (Sol high), briefed as a *doc* reviewer, read-only, given the doc paths plus the prototype/decision-log/ADR paths. On Codex: a one-shot `gpt-5.6-sol` `high` with the same brief.

The brief — findings first, ordered by severity, each citing the doc line and the evidence:

1. **TDD gate, adversarially:** find any AC / FL rule / EC a stranger could NOT write a failing test from — unquantified adjectives, missing precedence or fallback rules, undefined thresholds, decision tables with uncovered rows.
2. **Contradiction hunt:** any claim the residue disproves — doc vs. prototype source, `docs/decisions.md`, ADRs, CONTEXT.md terminology.
3. **Break-risk completeness:** existing behavior this change could break that the PRD's edge cases don't name (the user-visible-sequencing class of flaw — think like the customer receiving the output, not the code).
4. **Internal consistency:** task-vs-PRD drift, orphaned or duplicated IDs, coverage-matrix orphans in the Tests doc (either direction), Scope statements that disagree across the set, Open Questions answered elsewhere in the same set.
5. **Language regression pass (PRD + Tests doc):** the reader-effort editor has already done the dedicated editorial pass, so this item is narrower — verify the post-editorial text still passes the Simplicity gate's checks, and that no applied editorial fix drifted meaning (requirement strength, negations, conditions, thresholds, scope, IDs). Do not re-litigate style calls the editor already made. If the reader-effort pass was skipped this run, widen this item back to a full language-only pass against the Simplicity gate's checks.

Findings are **advice to the author, surfaced verbatim to the user** alongside the changes-or-create question — the user is the sole approver, and no finding is silently "fixed" without appearing in the presented list. Apply accepted findings through the edit loop (dependency check included). Timing: after the quality gates pass and the reader-effort pass's SAFE EDITORIAL fixes are applied, before presenting; default-on for engineering-bound sets, offered otherwise.

## Clarification ladder (when a contract is ambiguous or docs conflict)

1. **Gate finding** → try to resolve from the prototype code or existing docs first.
2. **Ask** — `AskUserQuestion` for quick, bounded calls (2–4 options with a recommended default).
3. **Grill** — invoke `/grill-with-docs` when the ambiguity is deeper: terminology clashes with CONTEXT.md, a call that contradicts a documented ADR, or a whole plan that needs stress-testing.
4. **Park** — if unresolvable in-session, it goes to **Open Questions with an owner and a stated working default**. Never a silent guess, never a vague adjective left in a flow.
5. Whatever gets resolved becomes a decision turn in the Handoff, so the answer survives the session.

## Pushing to Asana

Never push directly from this skill. On the user's "create" confirmation, invoke **`asana-create-task`** with the doc paths, task type, and prototype info. Local docs update first, always.

## Runtime portability (Claude Code + Codex share this file)

The canonical copy lives at `~/.claude/skills/refrens-feature-docs/SKILL.md`; `~/.codex/skills/refrens-feature-docs` is a symlink to it. **Edit only the canonical copy — never fork it per runtime.** When a referenced capability doesn't exist in the current runtime, substitute, don't skip:
- No `AskUserQuestion` tool → ask the question in plain chat with lettered options and a recommended default; wait for the answer.
- No `Skill` tool / slash-skill mechanism → read the companion skill file directly (`~/.claude/skills/asana-create-task/SKILL.md`, `~/.claude/skills/grill-with-docs/SKILL.md`) and follow its instructions inline.
- No `Agent` tool / named subagent registry (`Explore`, `codex-reviewer`, `reader-effort-editor`) → do the grounding-navigation pass yourself inline (same output contract: pointers + verbatim `file:line` quotes, not paraphrase) rather than delegating a call that doesn't exist here. For the doc var-check, use the one-shot `gpt-5.6-sol` `high` call the var-check section specifies instead of the `codex-reviewer` agent name. For the Codex reader-effort pass, first try an explicit fresh subagent with model `gpt-5.6-sol` and reasoning effort `xhigh`, following `~/.codex/skills/reader-effort-editor/SKILL.md`; only if neither named-agent nor explicit model-routed spawning is callable may you run the editorial pass inline. In that last fallback, follow `~/.claude/agents/reader-effort-editor.md` and report both lost guarantees: `reader-effort inline(self; model inherited; cold-read lost)`.
- No frontmatter-driven model selection → the `model: fable` / `effort: high` frontmatter is a Claude Code-only mechanism the harness uses to pick the **author** model. Codex cannot switch the current author to Fable. A Codex custom-agent TOML may still pin its own spawned worker's `model` and `model_reasoning_effort`; that is how the reader-effort editor gets Sol Extra High. On Codex, the config banner's author `model` field is always the real GPT model/profile this root session is already running under — never echo "fable" there.
- The **runtime manifest** (workflow step 7) always reports what actually ran on *this* runtime, not the other runtime's label — e.g. on Codex, `grounding inline(self)`, `reader-effort reader-effort-editor(gpt-5.6-sol xhigh)`, or `var-check gpt-5.6-sol(high)`, never a copy-pasted `Explore`/`codex-reviewer`/Fable label that has no meaning there. If a requested/default route did not apply, report the inherited model instead of the preferred one.
- The workflow, templates, gates, and ladder are runtime-independent — apply them identically everywhere.
