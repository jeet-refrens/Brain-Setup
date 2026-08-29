# Query library

Queries that worked, kept so nobody rebuilds them.

## Layout

Each entry is two files with the same name:

- `<slug>.json` or `<slug>.sql` — the runnable query. This is the source of truth.
- `<slug>.md` — the question it answers, how to run it, what the numbers mean, and
  what to watch out for.

Run one straight from here:

```bash
python scripts/mb.py run --db 2 --file docs/data/query-library/<slug>.json --collection <collection> --probe
```

## When to add an entry

Add one when a query took real work to get right, or when it is likely to be asked
again. Skip the one-off throwaways.

Every entry says **when it was last verified**. A query nobody has run for months is a
hypothesis, not an answer.

## Entries

| Query | Answers | Database | Last verified |
|-------|---------|----------|---------------|
| [documents-created-by-type](documents-created-by-type.md) | How many documents of each type were created in a date range | 2 `refrens` | 19 Aug 2026 |
| [businesses-created-by-day](businesses-created-by-day.md) | How many real businesses signed up in a date range, by day and by country, test accounts excluded | 2 `refrens` | 19 Aug 2026 |
| [so-to-invoice-lineitem](so-to-invoice-lineitem.md) | For one business, how much of each sales order line is invoiced and how much is still open, line item wise (live as Metabase question 5017) | 2 `refrens` | 25 Aug 2026 |
