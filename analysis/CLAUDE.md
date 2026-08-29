# analysis/ — data & Metabase analysis

This folder is for **Metabase / data-analysis work**, not product features. Each subfolder is
one analysis (a question and its answer). Build features under `features/`, not here.

## Before writing any query

**Read [`../docs/data/README.md`](../docs/data/README.md) first.** It holds the database map,
the confirmed field lists, the join map, and the guardrails.

Two things it will save you from:

- **The main database is MongoDB, not SQL.** Database 2 `refrens` takes aggregation
  pipelines. Only database 4 `Saturn` (accounting) takes SQL.
- **Never guess a field name.** 13,722 field paths are indexed locally. Look them up with
  `python scripts/mb.py fields <db> <collection> <pattern>`, or ask.

Run every query through `python scripts/mb.py` — it blocks the shapes that would scan a
production collection.

## Module context

- Read the relevant module's [`schema.md`](../docs/modules/) — **Summary first**. Only open the
  "Source of truth" repo (via `gh` CLI, `GITHUB_PAT` by name) if you need exact field-level
  precision the Summary doesn't give you.
- If the question spans more than one module, read
  [`cross-module-links.md`](../docs/cross-module-links.md) first so joins and impacts are right.
- Check [`glossary.md`](../docs/glossary.md) so you use the canonical term for each field/status.

## Deliverables for each analysis

Every analysis writes a `findings.md` that contains **both**:

1. **The query** — the actual pipeline or SQL used (and the Metabase question link if applicable).
2. **A plain-language answer** — what the numbers mean, in words, for a non-analyst reader.

Use `/analysis-kickoff <name>` to scaffold a new analysis (`question.md`, `queries.sql`,
`findings.md`) seeded with the relevant `schema.md` pointers.

## Secrets

Never print values of `METABASE_API_KEY`, `METABASE_URL`, `GITHUB_PAT`, or any other `.env`
var. Reference them by name only.
