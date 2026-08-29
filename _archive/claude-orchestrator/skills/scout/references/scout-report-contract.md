# Scout Report Contract

Every scout receives a destination, scoped questions, source references, cycle
number, run directory, and exact report output path.

## Full report

Write the full report to the assigned path using this shape:

```markdown
# <Scout role> report

## Assignment
## Scope investigated
## Sources checked
## Confirmed facts
## Strong inferences
## Contradictions
## Unknowns and access gaps
## Implications for the destination
## Recommended next probes
## Source index
```

Follow `evidence-standard.md`. Cite exact paths, lines, URLs, identifiers, and
observation dates where applicable. Keep raw logs and large code excerpts out
of the report; cite them instead.

## Navigation memo

Return only a compact memo to the Opus navigator, no more than 800 tokens:

```text
Scout:
Coverage:
Key confirmed facts:
Strongest inference:
Contradictions:
Blocking unknowns:
Confidence: high | medium | low
Recommended next probe:
Full report:
```

## Behavioral rules

- Investigate only the assigned domain and questions.
- Do not implement, edit source files, or make state-changing external calls.
- Write only the assigned report artifact.
- Do not ask the user questions.
- Return ambiguity instead of guessing.
- Do not recommend a final solution unless the assignment explicitly asks for
  options; even then, separate evidence from preference.
- A follow-up cycle should discriminate between explanations, not repeat the
  original broad search.
