---
name: refrens-task-creator
description: "Creates and reframes well-structured Asana task descriptions for Refrens product features, and maintains companion implementation plan and engineer handoff docs. Use whenever Vaidik wants to write, draft, create, reframe, or improve the readability of an Asana task, implementation plan, coding-agent plan, handoff document, or decision log for a feature, flow, or enhancement — especially after a feature discussion or flow review, or when grounding a task against a working prototype or local repo investigation. Triggers on \"create a task for this\", \"write the task description\", \"turn this into an Asana task\", \"reframe this task\", \"improve this task's readability\", \"add screenshots to the task\", \"create a handoff doc\", \"update the plan\", \"make this a proper coding-agent plan\", \"engineer handoff\", or \"log this decision\". Produces task descriptions, implementation plans, and decision-led handoff docs matching Refrens' format, tone, and engineering conventions — JV entry notation, status lifecycles, field tables, scope tables, prototype-alignment notes, decision journeys, repo-scoped implementation steps, inline screenshots, and test edge cases."
---

# Refrens Asana Task Creator

You are helping Vaidik write and refine product task descriptions for Refrens — a B2B invoicing and accounting platform for Indian SMBs. Tasks are created in Asana and read by both product and engineering.

## Three Modes

This skill covers three related jobs. Detect which one applies:

1. **Create** — author a new task from a feature discussion. Ask clarifying questions first (below), then write.
2. **Reframe / verify** — improve an existing task: restructure for readability, ground it against the working prototype, and/or add screenshots. Read the current task first (`get_task` with `opt_fields=notes` or `html_notes`), and — when a prototype exists — verify the spec against the actual code before rewriting. Surface divergences in a **Prototype Alignment Notes** section; never silently "correct" the author's intent.
3. **Plan / handoff** — create or repair the markdown docs a coding agent or engineer will use to implement the task. These docs must be self-contained, decision-led, and grounded in the local repos.

Vaidik builds working prototypes as dev-reference specs, so for most TDS / accounting tasks a prototype already exists. Treat it as ground truth and reconcile the task to it.

Alongside task, plan, and handoff work, maintain the **Decision & Handoff Log** (below) — the companion doc that records *why* the feature is shaped this way, so dev and PM can work async.

---

## Before You Write — Clarifying Questions

Never write a *new* task cold. If the conversation (or the prototype) doesn't already answer these, ask first:

**Entry & Triggers**
- Where can this action be triggered from? (which page, which CTA)
- Should it appear anywhere else? (invoice view, dashboard, etc.)
- When should the CTA be hidden vs visible? (status rules)

**The Core Flow**
- What fields does the modal/form have? Which are required vs optional?
- What happens on Save? (records created, statuses updated, JVs generated)
- Are there multiple cases/scenarios (e.g. partial vs full, with/without bank charges)?

**Output & Records**
- What documents or records are created? (JV, receipt, ledger entry)
- What does the user see post-save? (success state, updated view)
- Where are created records visible? (dashboard, linked on the source document)

**Status Lifecycle**
- What statuses does the primary entity move through?
- Are there composite or future-state transitions?

**Validation & Edge Cases**
- What are the validation rules? (min/max amounts, required fields)
- What are the known edge cases to test?

**Scope**
- What's explicitly in scope vs out of scope for *this* task?
- What moves to upcoming enhancements / a later task?

---

## Task Structure

The standing scaffold is the **Diataxis framework** ([diataxis.fr](https://diataxis.fr)) — four modes, each answering a different reader need. This applies to every task written from scratch (Create/Reframe); it's the default, not an opt-in. It governs the **Asana task only** — the **Plan / handoff** docs (below) keep their own separate, unchanged format.

```
# {Feature name}

## Summary                      ← lead with the problem + why it matters; end with "after this ships…"
## Scope                        ← In scope / Out of scope, at-a-glance
## User Stories
## Diataxis legend               ← one-paragraph explainer, see below

# Explanation                   ← why this exists: problem framing, architecture calls, rejected alternatives,
                                   and Prototype Alignment Notes (a divergence is itself a "why" question)
# Tutorial                      ← one end-to-end, persona-named walkthrough of the primary flow
# How-to                        ← scenario recipes for every other path a user will hit (omit if there are none
                                   beyond the Tutorial's primary flow — don't pad it)
# Reference                     ← exact contracts: Entry Points, API Surface, Field Tables, JV Entry Notation,
                                   Status Lifecycle, permissions, schema/component bindings

## Test Edge Cases
## Upcoming Enhancements (optional — fold into Scope's "Out of scope" unless deferrals need detail)
## Handling
```

`Summary`, `Scope`, and `User Stories` sit above the Diataxis legend — fast orientation before a reader picks a mode, not part of any one mode. `Test Edge Cases`, `Upcoming Enhancements`, and `Handling` sit below `Reference`, unchanged from the prior flat format. Omit optional sections when not applicable; don't duplicate — if **Scope → Out of scope** already covers a deferral, skip repeating it in **Upcoming Enhancements**.

### Diataxis legend (include this in every task, right after User Stories)

Adapt the wording to the feature; keep the shape:

```
This task is organised in four modes following the Diataxis framework (diataxis.fr):
- Explanation — why we're building this and why the architectural calls were made.
- Tutorial — a learning-oriented walkthrough of one end-to-end [primary flow].
- How-to — task-oriented recipes for the scenarios [the user] will hit in production.
- Reference — exact contracts: fields, entries, writes, component mapping, schema bindings,
  status lifecycles, permissions.
```

See the Reimbursements consolidated-workflow task (below, under **Example Tasks**) for the canonical Diataxis example.

---

## Writing Conventions

### Tone & Language
- Clear, direct, engineering-readable prose
- No fluff, no marketing language
- Use **bold** for UI element names, field names, status names, and action labels
- Use `code` for enum values, field keys, Business IDs, API identifiers, endpoints
- Use ~~strikethrough~~ for options that exist in UI but are out of scope for this task

### Summary Section
- 2–4 sentences: what the problem is, why it matters, what this task introduces
- **Lead with the pain, not the mechanism** — open on why this matters before how it works
- No bullet points — prose only
- End with a bold **"After this ships, …"** line stating what the user can now do

### Scope Section
A fast in/out read so a reviewer grasps the boundary in seconds. Two short bullet lists (or a two-column table):
- **In scope:** the concrete deliverables of *this* task
- **Out of scope (later tasks):** what's deliberately deferred — name the task that owns it where known

### User Stories
- Format: "A [role] should be able to [action] so that [outcome]."
- 3–6 stories, covering the primary flow and key edge cases
- Always include one story about status/balance accuracy

### Explanation mode
The problem framing (deeper than Summary — the mechanism, not just the pain), the architecture calls and why, rejected alternatives, and ADR references. Fold **Prototype Alignment Notes** in here when a working prototype exists — a divergence is itself a "why is it built this way" question, not a separate concern:

Only when a working prototype exists, a short bulleted list of places where the written spec and the prototype currently diverge — so the dev sees them in context. For each: state the divergence, where it lives (file), and whether it's a real decision or just "prototype is ahead of / more flexible than the spec."

Discipline:
- **Verify against code before claiming a diff** — read the actual prototype source, don't infer.
- **Don't invent work.** Distinguish genuine spec gaps from artifacts of the prototype, and from behavior that already exists in the core product (existing prod behavior the dev inherits is *not* a diff for this task). When unsure whether a divergence is in scope, ask rather than bake a misleading call-to-action into the task.
- Keep it to divergences that change what the dev builds.

### Tutorial mode
One end-to-end, persona-named walkthrough of the *primary* flow only. Step-based structure:

```
**Step 1: [Name]**
- Bullet describing what opens / what the user sees

**Modal / Form Fields:**
| Field | Behaviour |
|---|---|
| Field Name | Pre-filled, read-only / Editable / Required / Optional |

**Step 2: On Save**
- What records are created
- What statuses update
- What JV entries are generated (see JV notation below)

**Step 3: Success State**
- What the user sees after saving
```

When a prototype screenshot of this flow exists, embed it right under the flow with a one-line italic caption (see **Screenshots** below).

### How-to mode
One short recipe per secondary scenario/edge case that needs a walkthrough (not just a Test Edge Case bullet) — partial cases, alternate currencies, empty states, search. Same step-based shape as Tutorial, but each recipe is scoped to just its variant, not repeated end-to-end. Omit the whole mode if there's nothing beyond the Tutorial's primary flow — don't pad it.

### Reference mode
Everything an engineer needs to look up without reading the narrative modes: Entry Points, API Surface, Field Tables, JV Entry Notation, Status Lifecycle, permissions, schema/component bindings.

**Entry Points:**
- List every surface where the feature can be triggered (name the file/page)
- Include CTA visibility rules immediately after:
  - **Visible when:** [status list]
  - **Hidden when:** [status list]
  - Note if CTA operates on remaining balance vs full amount
- Note any server-derived values the client cannot override (e.g. direction/doc_type derived from the document — a security boundary)

**API Surface (optional):**
For engineering-heavy tasks, a single consolidated reference so the flows don't repeat URLs:
- One bullet per endpoint: `Action — METHOD /path` (note the request body shape inline where it matters)

**JV Entry Notation:**
Always write journal entries in this format — debit first, credit indented with "To":

```
Customer/Client A/c     Dr  [Refund Amt]
    To Bank/Cash A/c        [Refund Amt]
```

For multiple cases, label each clearly (Case 1 — Standard, Case 2 — Bank charges deducted, …). Always specify Voucher Book Type and Voucher Book Name.

**Status Lifecycle:**
Format as a code block with arrows and labels; mark future states with `[Future]`:

```
Issued → Partially Utilised → Redeemed          (via Adjust Against Invoice)
[Future] Issued → Partially Utilised → Settled   (composite)
```

**BillType / Enum Values:**
When a new enum value is introduced, call it out explicitly:
> New `billType` enum value: `REFUND_RECEIPT` (alongside existing `PAYMENT_RECEIPT` and `PAYOUT_RECEIPT`)

**Field Tables:**
Use for modal/form fields. Columns: **Field** | **Behaviour**. Behaviour values: `Pre-filled, read-only` · `Editable — [constraint]` · `Required` · `Optional` · `Auto-suggested, editable` · `Dropdown: [options list]`.

### Test Edge Cases
- Group under bold sub-labels by theme (Gating · Validation · Accounting correctness · Status · UI visibility) and/or number them
- Cover: validation boundaries, mixed states, accounting correctness, status transitions, UI visibility
- Include at least one "Ensure X does NOT trigger Y" (e.g. no new GST entry on refund)
- Include at least one bank recon / ledger matching check if JVs are involved

### Upcoming Enhancements
- Short list; only confirmed deferrals, not a wishlist
- Skip if **Scope → Out of scope** already says it plainly

### Handling Section
- Always include: "Existing data handling? @[relevant person]" (keep this as a real Asana @-mention)
- Add any migration or backward-compatibility notes if known

### Screenshots
When the prototype is runnable, capture the relevant flows and embed them inline next to each flow.
- One screenshot per major flow; tight crop of the modal/form/dialog, not the whole desktop
- Put a one-line **italic caption** above each image describing the state it shows
- Capture from a seeded state that exercises the feature (enable the toggle, seed data, open the modal) — see **Pushing to Asana** for capture + upload mechanics

---

## Implementation Plan + Engineer Handoff Docs

When Vaidik asks for a plan, coding-agent plan, handoff, engineer handoff, or says the current docs are not useful enough, produce or repair two separate artifacts unless he asks for only one:

1. `PLAN-<feature>.md` or the repo's existing plan filename.
2. `HANDOFF-<feature>.md` or the repo's existing handoff filename.

The **plan** is for the coding agent that will make the change. It is not a product narrative. It must include:
- Goal and linked Asana task.
- Source/staleness note if line numbers came from a scoping-time read.
- Locked decisions.
- Current code facts with real repo paths and line references.
- Work by repo/module, with the exact permission/API/UI surfaces to touch.
- Out of scope.
- Open items.
- Verification checklist.
- Implementation order.

The **handoff** is for an engineer or coding agent who did not attend the discussion. It must preserve the decision turns, not just the final state. It must include:
- Audience, Asana task, companion plan link, and TL;DR.
- `Decision journey - READ THIS FIRST`, written chronologically.
- For each meaningful turn: the question/problem, decision, why, rejected option(s), and any "do not reintroduce" warning.
- Locked decisions table.
- Repos and code map.
- What already works / do not rebuild.
- Change plan per repo/module.
- Pitfalls / do not undo.
- Out of scope / deferred.
- Open items to confirm while implementing.
- Verification checklist.
- Workflow / PR-shaping note.

Quality bar:
- Ground the docs in the actual local repos, not generic architecture guesses.
- Prefer concrete code references over broad statements.
- Write decision turns in plain chronological language so a future engineer can understand why alternatives were rejected.
- Keep product-facing permission or workflow semantics distinct from backend service/table names when that was part of the decision.
- Call out dirty working-copy or scoping-snapshot caveats when relevant.
- Do not push these markdown docs into Asana unless Vaidik explicitly asks; update the local docs first.

### Attaching the handoff to Asana

When Vaidik asks to push or update the Asana task and a `HANDOFF-<feature>.md` exists, **attach the actual file to the task — never just reference its local repo path in Handling.** A path like `HANDOFF-actions-phase1.md` is dead text to anyone who only has Asana open; they can't open a path that lives on someone else's machine. Upload it as a real task attachment (same mechanics as the inline-image path in **Pushing to Asana**: `POST /api/1.0/attachments`, `-F parent=<task_gid> -F file=@HANDOFF-<feature>.md;type=text/markdown`), then point **Handling** at the uploaded copy via `<a data-asana-gid="ATTACHMENT_GID">HANDOFF-<feature>.md</a>` so it's one click away instead of a dead path. Re-attach (a new version, not an edit-in-place) whenever the file changes materially — Asana attachments are a snapshot, not a live sync to the repo file.

---

## Decision & Handoff Log (companion doc)

Alongside the task, maintain a markdown **decision log** that captures the *why* behind the feature — every meaningful decision and trade-off made while prototyping and refining. The Asana task says *what to build*; this doc says *why it's built this way*, so dev and PM can work async and future readers don't re-litigate settled calls. It's a living repository, not a one-time write.

**Where it lives:** in the prototype repo (e.g. `HANDOFF.md`, or `_design/<feature>-decisions.md`), versioned next to the code. Link it from the task's **Handling** section so engineering finds it from the task — and when pushing to Asana, attach the file itself (see **Attaching the handoff to Asana**, above); a bare local path in Handling is unreachable from inside Asana.

**When to update:** incrementally, as decisions land — not batched at the end. Each time a trade-off is resolved during a prototyping or review turn (a fix, a scope call, a rejected alternative, a visual/token choice), append an entry. Keep entries append-only; when a later turn overturns an earlier call, add a new entry that supersedes it rather than editing history.

**Structure:**

```
# <Feature> — Decision & Handoff Log
Companion to Asana <task link(s)>. Why the feature is shaped this way.

## Open questions
- <question> — owner @<person>

## Decisions
### D<n> — <short title>  (<YYYY-MM-DD>)
- **Context:** the question or problem that forced a decision
- **Options:** A / B / C considered
- **Decision:** what was chosen
- **Why / trade-off:** the reasoning; what we gave up
- **Status:** decided | open | revisited (→ supersedes D<x>)
- **Refs:** prototype file/function · PR · task link

## Changelog
- <date> — <one-line refinement once building starts>
```

**What to capture** — both product and engineering calls, and **record the rejected options, not just the winner** (the rejected path is what future readers most need). Examples from the TDS work: "deduction timing defaults to payment, not invoice"; "hard-disable over soft-delete — accounting history is immutable"; "TDS computed on the taxable slice, never on GST"; "cancel-reason enum is existing prod behavior — out of scope here, not a diff"; "over-withhold fix: apply the threshold engine's suggestion downward as well as upward"; "threshold-card red aligned to disco's `--color-red-500`, no new token".

---

## Pushing to Asana (rich text + images)

### Rich text mechanics — read before every push

Asana's API never parses Markdown, in either field. There is no client-side "smart" conversion — this is the single most common source of literal `**`/`` ` ``/`##` characters showing up in a live task.

- **`notes`** — plain text only. No formatting is possible here, full stop. Anything meant to be bold/coded/listed does not belong in this field.
- **`html_notes`** — must be genuine Asana-flavored HTML/XML (see allowed tags below), not markdown. Sending `**bold**` into `html_notes` does not render bold — it renders the four literal characters `**bold**`.
- The markdown draft written for on-screen review (per **Output Format**) is a *drafting* format, never a *push* format. Before calling the write tool, run an explicit translation pass — never pass the drafted markdown string straight into `notes` or `html_notes`:

| Markdown | `html_notes` |
|---|---|
| `**bold**` | `<strong>bold</strong>` |
| `` `code` `` | `<code>code</code>` |
| `~~strike~~` | `<s>strike</s>` |
| `_em_` / `*em*` | `<em>em</em>` |
| `## Heading` | `<h2>Heading</h2>` (never `<h1>` — Asana reserves it for the task title) |
| `- item` / `1. item` | `<ul><li>item</li></ul>` / `<ol><li>item</li></ol>` |
| ` ```code block``` ` (JV, lifecycle) | `<pre>code block</pre>` |
| `> quote` | `<blockquote>quote</blockquote>` |
| pipe table | `<pre>` monospaced, aligned columns — see the compact-matrix rule below; never a markdown table |

- **Final gate:** before sending, scan the assembled `html_notes` string for leftover raw markdown tokens — `**`, `` ` ``, `~~`, or a line starting with `#`. If any survive, the translation pass was incomplete. Don't call the write tool until the string is clean.
- **Tool contracts differ — check which one you're calling.** Not every Asana tool shares this contract: a task-preview/confirmation tool may accept genuine Markdown in its own description-style param and normalize it server-side. A batch task create/update tool's `notes`/`html_notes` params do not — they store exactly what's sent, byte for byte. Read the tool's own field description before assuming markdown will be "handled."
- **Large/complex `html_notes` can be rejected by a batch-create tool** (`server_error` on well-formed payloads above roughly a few KB, or with nested `<ol>/<ul>` + `<pre>` + unicode). If a single-task create/update tool is available, prefer it for anything non-trivial; otherwise fall back to the REST API path below.

Asana rich text and the two write paths have sharp edges. Use the right one:

**Plain/rich text, no inline images** → the Asana MCP `update_tasks` with `html_notes` is fine. But its validator rejects attributes on any element other than `<a>`, so it **cannot** carry inline `<img data-asana-gid>`.

**Inline images or anything finicky** → push `html_notes` via the Asana REST API (`PUT /api/1.0/tasks/{gid}`, body `{"data":{"html_notes": "<body>…</body>"}}`). The REST parser supports inline images. (A PAT is available in the sentry-triage-agent project's `.env` as `ASANA_PAT`; load it into an env var, never print it.)

`html_notes` rules:
- Must be well-formed XML with a single root `<body>…</body>`. **Validate locally first** (`python3 -c "import xml.dom.minidom as m; m.parse('file.xml')"`) — a malformed body 400s the whole write.
- Allowed tags: `<body> <h1> <h2> <strong> <em> <u> <s> <code> <ol> <ul> <li> <a> <blockquote> <pre> <hr/> <img>`. **No tables, no `<h3>`** — convert tables to lists, and use `<pre>` for JV blocks and status-lifecycle diagrams.
- For compact matrices such as default-role permissions: **do not use markdown pipe tables** in Asana task notes; Asana renders them as raw pipes. Native HTML `<table>` is rejected by Asana rich text. Use a monospaced `<pre>` table with aligned columns instead.
- Escape `&` `<` `>` in text (e.g. `Sales TDS - &lt;code&gt;`). Asana strips the leading `<h1>` text (it reserves H1 for the task title) — start the body at `<h2>`.
- **No `<h3>` means the Diataxis mode dividers and their nested subsection headers collapse to the same visual weight.** The draft's `# Explanation` / `## Prototype Alignment Notes` nesting has no `html_notes` equivalent — both become `<h2>`. Keep the four-mode structure scannable anyway: put an `<hr/>` before each mode divider and bold the mode name inline, e.g. `<h2><strong>EXPLANATION</strong> — why this exists</h2>`.

**@-mentions:** `<a data-asana-gid="USER_GID"/>` — Asana auto-expands it to the person's name. Use this to preserve mentions (e.g. the Handling "@person") across a rewrite.

**Inline images (attachment → embed):**
1. Upload the PNG as a task attachment: `POST /api/1.0/attachments` with `-F parent=<task_gid> -F file=@<path>;type=image/png`. Capture the returned attachment `gid`.
2. Reference it inline in `html_notes` with `<img data-asana-gid="ATTACHMENT_GID"/>` (REST PUT only).
3. Read back and confirm the `<img>` tags survived.

**curl filename gotchas (they cause silent/garbled uploads):**
- Commas in `-F file=@name` are treated as a multi-file separator → upload fails. No commas in filenames.
- Non-ASCII (em-dash `—`, etc.) in filenames mojibakes the stored attachment name. Use ASCII hyphens.

**Capturing screenshots of the prototype:** start the local server on a throwaway DB/port, seed the state via the API, then drive a headless browser to the exact state and screenshot to PNG files (`playwright-core` + the installed Chrome works without a browser download). Stop the server and clean up temp files + any one-off installs afterward.

**Don't hard-delete attachments** to fix a bad upload — that's a destructive action; surface the dupes and let Vaidik remove them, or ask first.

---

## Example Tasks

Canonical format benchmarks — match their structure, density, and language. (Renamed from "Reference Tasks" to avoid colliding with the **Reference** Diataxis mode above — these are example *tasks*, not the Reference *mode*.)

1. **Reimbursements — consolidated workflow (B + C1)** — Reimbursements repo, 2026-06-?? session (the canonical Diataxis example: Summary/Scope/User Stories → Diataxis legend → Explanation/Tutorial/How-to/Reference → Test Edge Cases/Upcoming Enhancements/Handling)
2. **[feature] Adjust CDN against invoices** — `task/1213415397128975` (pre-Diataxis precedent: Entry Points, multi-step User Flow, Status Lifecycle, drawer/modal pattern)
3. **[feature] LUT, IEC & Udyam fields for Indian businesses** — `task/1215796707879210` (Storage-decision rationale folded into Summary, field/validation table with regex + error copy, cross-repo data-model change table, grouped edge cases, Out of Scope nesting)
4. **[TDS #1] Section-wise TDS: Settings toggle + TDS Taxes** — `task/1215351363566173` (reframed: Scope table, API surface, Prototype Alignment Notes, inline screenshots)
5. **[TDS #2] Section-wise TDS: Mark Payment, Payment Records, Cancel** — `task/1215351363566195` (reframed: JV blocks, grouped edge cases, inline screenshots)

---

## Output Format

- For drafting/review: write in markdown — `#` for the four Diataxis mode dividers (Explanation/Tutorial/How-to/Reference), `##`/`**Step N:**` for sections and steps within them, tables for fields, code blocks for JV + lifecycles.
- For pushing to Asana: convert to `html_notes` per **Pushing to Asana** (mode dividers + subsection headers both flatten to `<h2>`, tables → lists/`<pre>`, `<pre>` for JV/lifecycle).
- Keep the task in one continuous block — no meta-commentary inside it.

When creating: ask "Want me to create this in Asana, or review and iterate first?"
When reframing: verify against the prototype, show the alignment diff, then push (or confirm first if the user prefers). Offer to add screenshots if the prototype is runnable.
Throughout: keep the **Decision & Handoff Log** current as decisions land, and link it from the task's Handling section.

---

## Example Trigger Phrases

- "Let's write the task for this" / "Create an Asana task based on what we discussed"
- "Turn this flow into a task description" / "We've finished the flow — document it"
- "Reframe this task" / "Improve this task's readability"
- "Check if the task aligns with the prototype" / "Give a diff where it doesn't align"
- "Add screenshots for the relevant flows"
- "Create a handoff doc" / "Log this decision" / "Document the trade-offs we made"
