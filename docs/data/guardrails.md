# Query guardrails

These are production databases. A careless query is a real incident, not a slow page.

Most of these rules are **enforced in code** by `scripts/mb.py`, so they cannot be
forgotten under time pressure. The rest need judgement and are marked as such.

## The two rules everything else serves

1. **Never guess a field.** If it is not in the field index or in
   [verified/](verified/), stop and ask. A query on a field that does not exist
   returns zero rows, and zero rows looks like an answer.
2. **Never read a whole collection.** Filter first, on something indexed.

## MongoDB (db 2 `refrens`)

**Enforced by the script:**

| Rule | Why |
|------|-----|
| The pipeline must start with `$match`, or carry a `$limit` in the first two stages | A bare `$group` or `$sort` reads every document |
| Every field in the opening `$match` must exist in the field index | Catches typos and invented names |
| The opening `$match` must touch at least one **indexed** field | Metabase records which fields are indexed. An unindexed filter is a full scan wearing a filter's clothes |
| High-volume collections must have a date range in the opening `$match` | Listed below |
| `$lookup` must carry a sub-pipeline with its own `$match` | A plain `$lookup` reads the whole joined collection |
| `$out`, `$merge`, `$where`, `$function`, `$accumulator` are refused | The first two **write to the database**. The rest run arbitrary JavaScript on the server |
| A `$limit` is added if the pipeline does not end in an aggregate | Default 2,000 rows |

**High-volume collections — a date range is required, no exceptions:**
`axiosrequests`, `logs`, `activities`, `notifications`, `feeds`, `invoiceaudits`,
`salesactivities`, `contactactivities`, `contactActivities`, `leadpipelinehistories`,
`outboundcalls`, `calls`.

Add to that list in `scripts/mb.py` whenever a collection turns out to be bigger than
it looked.

**Needs judgement:**

- Prefer two cheap steps to one clever one. Collect ids, then `$in`. That is the
  pattern the existing saved questions use.
- `$group` over a wide date range is still expensive even when it is legal. Check the
  probe count first.
- `$unwind` on a large array multiplies the document count. Filter before it, never
  after.

## Postgres (db 4 `Saturn`)

**Enforced by the script:**

| Rule | Why |
|------|-----|
| `SELECT` and `WITH` only | Read only, always |
| `insert`, `update`, `delete`, `drop`, `alter`, `truncate`, `create`, `grant`, `revoke`, `copy`, `vacuum`, `reindex` are refused | Same |
| One statement only | Blocks a second statement smuggled in after a semicolon |
| `LIMIT` is added when missing | Default 2,000 rows |
| These tables are refused: `query_performance_logs`, `pg_stat_statements`, `pg_stat_statements_info`, `pg_buffercache`, `job_run_details` | Diagnostic tables, huge and useless for product questions |
| A missing `WHERE` produces a warning | See below |

**Needs judgement:**

- **Filter on `business`.** On every business-scoped Saturn table, the only indexed
  columns are `id` and `business` (confirmed 19 Aug 2026). Anything else is a full
  table scan.
- `voucher_entries`, `lineitems` and `bank_statements` are the wide, heavy ones.
  `voucher_entries` has 66 columns, many of them one per currency.
- Saturn has the Citus and pg_partman extensions installed, but `citus_tables` is
  empty, so the tables are **not** distributed today. Do not write a query that
  assumes sharding, and do not assume a partition prune will save you.

## Probe before you run

`python scripts/mb.py run ... --probe` runs the opening `$match` with a `$count`
first, and prints how many documents it selects. That number is the cost signal.

Rough reading:

- under ~100,000 matched documents: fine
- 100,000 to 1,000,000: fine for a `$group`, slow for a full row dump
- over 1,000,000: tighten the filter, or say what it will cost and ask first

## Overriding a guardrail

`--override "<reason>"` exists. Using it means:

1. Say what you are doing and why, **before** running it.
2. Write it in [learnings.md](learnings.md) with the date.
3. If the rule was wrong, fix the rule in `scripts/mb.py` instead of overriding it
   again next time.

An override with no stated reason is not allowed.

## Numbers that are true but misleading

- **Test and internal accounts are in the data.** The house pattern in existing saved
  questions is to exclude emails containing `test` or `refrens`. Say whether you
  excluded them.
- **`isRemoved` and `isHardRemoved` are soft-delete flags.** Counting documents
  without them counts deleted ones.
- **Roughly 40% of users are outside India.** Never present an India-only number as a
  total. Check whether the question needs splitting by country.
