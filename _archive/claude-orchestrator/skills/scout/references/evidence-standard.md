# Evidence Standard

Label every material statement with one epistemic status:

- `CONFIRMED`: directly supported by inspected evidence.
- `INFERRED`: best explanation of confirmed facts, but not directly observed.
- `ASSUMED`: temporary premise needed to proceed; user or source has not
  confirmed it.
- `UNKNOWN`: material question with insufficient evidence.

## Source priority

Use the source closest to actual behavior. A practical ordering is:

1. Direct production observation or authoritative runtime telemetry
2. Deployed version and runtime configuration evidence
3. Current production codepath and tests
4. Merged PR, commit, or migration evidence
5. Task descriptions, design docs, ADRs, comments, and recollection

Higher-ranked evidence does not automatically erase lower-ranked intent. A
production observation explains what happens; a contract or task may explain
what was supposed to happen. Preserve that distinction.

## Source references

For every material confirmed fact, cite the most precise available pointer:

- Local file path and line reference
- PR or commit URL and relevant file/diff
- Task or document URL and section
- Production URL, request, screenshot, query, dashboard, or log identifier
- Command used and the relevant result
- Observation date when production or deployment state can drift

Do not cite a search result when the underlying source is available. Do not use
an unmerged branch as evidence of production behavior.

## Contradictions

Record contradictions explicitly:

```text
Claim A:
Evidence for A:
Claim B:
Evidence for B:
Most likely explanation:
What would discriminate:
Status: open | resolved
```

Never smooth conflicting evidence into a vague summary.

## Negative evidence

Absence is evidence only when the search surface was sufficiently bounded.
State where and how you searched before claiming that something does not exist.

## Production language

Use these phrases precisely:

- `Verified in production`: directly observed against the production surface.
- `Consistent with production`: indirect evidence aligns, but no direct
  observation was possible.
- `Present in merged code`: merged, but deployment was not verified.
- `Present on the inspected branch`: no production claim.
- `Unverified`: evidence or access was insufficient.
