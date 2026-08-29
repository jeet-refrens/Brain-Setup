# Scouting Dossier Template

Use this structure for `SCOUTING_DOSSIER.md`.

```markdown
# Scouting Dossier: <problem>

## Executive conclusion
State the real problem, current production reality, and recommended next move.

## Inputs and scope
- Problem statement
- Previous task
- Relevant PRs / commits / deployments
- Production surfaces
- In scope
- Out of scope
- Observation dates

## Confidence legend
Define CONFIRMED, INFERRED, ASSUMED, and UNKNOWN.

## Current production understanding
Describe the end-to-end behavior that exists today. Separate verified
production behavior from merged code and branch-only behavior.

## What exists today

## What was already solved

## What was partially solved

## What was not solved

## Claims versus reality
| Claim | Claimed source | Observed reality | Verdict | Evidence |
|---|---|---|---|---|

## Real problem after scouting
- Original framing
- Reframed problem
- Why the distinction matters
- What this is not primarily a problem of

## Relevant architecture and codepaths
Group by repo, service, package, or ownership boundary.

## Gap ledger
| Gap | Type | Impact | Evidence | Blocking? | Proposed owner |
|---|---|---|---|---|---|

## Material contradictions

## Decision points
For each: question, options, recommendation, tradeoffs, owner, and blocking
status.

## Recommended next move
- Recommended path
- Why this path
- Rejected alternatives
- Ordered sequence
- Acceptance criteria
- Verification plan
- Rollout / migration considerations

## Risks and failure modes

## Assumptions and unresolved questions

## Source index

## Scout run metadata
- Run directory
- Cycles completed
- Agents used
- Fable escalation used: yes | no
- Last refreshed
```

Prefer direct conclusions backed by evidence over a chronological dump of what
the scouts read.
