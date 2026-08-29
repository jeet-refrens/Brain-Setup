# Clarification And Stop Rules

## Clarification gate

Ask the user only when the answer could change investigation scope, product
intent, architecture direction, production interpretation, or the recommended
next move.

Ask one high-leverage question at a time. Include:

- Why the answer matters
- The credible interpretations
- The recommended interpretation

Scouts never question the user directly. They return clarification candidates
to the navigator as either `blocking` or `non-blocking`.

Proceed with a labeled assumption when uncertainty is non-blocking. Record the
assumption in `SCOUT_MAP.md` and the final dossier.

## Evidence sufficiency

Stop scouting when all material conclusions meet these conditions:

- Production behavior is verified or explicitly marked unverified.
- Prior task and PR claims have been reconciled with production and code.
- Material contradictions are resolved or preserved as explicit blockers.
- Remaining unknowns would not change the recommended next move.
- The recommendation has acceptance criteria and a verification path.

Do not stop merely because every initial scout returned. Do not continue merely
because more files could be read.

## Soft three-cycle checkpoint

Three cycles are a checkpoint, not a hard cap. After cycle three, continue only
when the latest cycle produced material new evidence and the next question is
sharply narrower.

Before another cycle, state:

1. What changed in the evidence
2. Which decision remains blocked
3. The single discriminating question for the next cycle
4. Why Opus, Fable, or the user is not a better next step

If those statements cannot be made, stop and ask the user or recommend Fable.

## Fable escalation

Fable escalation is appropriate for persistent material contradictions,
multiple plausible framings with different consequences, and high-impact
decisions where additional repo reading is unlikely to settle the choice.

The navigator recommends escalation but never invokes it. The user must run:

`/scout-escalate <run-dir>/DECISION_PACKET.md`
