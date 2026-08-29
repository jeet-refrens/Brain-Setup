# Metabase map

Which database holds what, and where saved questions go.

Last confirmed against the live instance: **19 August 2026**.
Regenerate the raw lists with `python scripts/mb.py sync`.

## Databases

`python scripts/mb.py dbs` prints this from the cache.

| id | Name | Engine | What it holds | Use it for |
|----|------|--------|---------------|------------|
| **2** | `refrens` | **MongoDB** | The main product database. 118 collections. Businesses, users, documents, clients, leads, inventory, GST filings. | Almost every question |
| **4** | `Saturn` | **Postgres** | The accounting service. Vouchers, ledgers, line items, bank books, reconciliation. 33 tables. | Anything about books, ledgers or reconciliation |
| 3 | `courier` | MongoDB | Not yet mapped | Ask before using |
| 5 | `Riften` | MongoDB | Not yet mapped | Ask before using |
| 6 | `Whiterun` | MongoDB | Not yet mapped | Ask before using |
| 7 | `Stella` | MongoDB | Not yet mapped | Ask before using |
| 8 | `marika` | Postgres | Not yet mapped | Ask before using |
| 9 | `marika_stage` | Postgres | Staging copy of `marika` | Not for real numbers |
| 10 | `Serana Index Stats` | MongoDB | Index statistics | Its metadata call timed out at 2 minutes on 19 Aug 2026. Not in the cache. |
| 11 | `MRR Analytics` | Postgres | Revenue reporting | Ask before using |

Only **2** and **4** are in the local field index. To add another:
`python scripts/mb.py sync --dbs 2,4,11`.

### The two that matter

**db 2 `refrens` is MongoDB.** Queries are aggregation pipelines written as a JSON
array, not SQL. Metabase also needs to be told the source collection, which is what
`--collection` is for.

`ObjectId("...")` and `ISODate("...")` are fine to write. `scripts/mb.py` understands
them, checks the query, and sends them through unchanged.

**db 4 `Saturn` is Postgres.** Ordinary SQL. See
[verified/saturn-postgres.md](verified/saturn-postgres.md) for the shape of it.

## Metabase collections (the folders questions live in)

`python scripts/mb.py` sees only four:

| id | Name | Can this API key write to it? |
|----|------|-------------------------------|
| `root` | Our analytics | yes |
| 3 | Automatically Generated Dashboards | no |
| 70 | IDC Technologies | yes |
| 134 | MRR Analytics | yes |

There are **3,858 saved questions**, and 3,723 of them sit loose in `root`. They are a
good source of proven query patterns. Search them with
`python scripts/mb.py cards "<text>"` and read one with `python scripts/mb.py card <id>`.

**`scripts/mb.py` never edits them.** It can search, read and create, and that is all.

Editing an existing question is still possible with a direct `PUT /api/card/<id>`, and it
was done once, on 21 August 2026, for card **5017 `[BEP] Order Management`** at Jeet's
explicit request. What made it safe:

- The card sits in `root` and reports `can_write: true`. A card in a collection this key
  cannot see returns 403, the same as collection 129 below.
- The full card JSON was saved to a backup file **before** the write.
- The card had no pinned `visualization_settings["table.columns"]`, so column order comes
  from the query's final `$project`. If a card does pin it, changing the query alone will
  not reorder the table.
- `result_metadata` was sent as `null` so Metabase rebuilds the stale column list.

Do not edit a saved question without being asked to. Back it up first when you are.

### Where saved questions go

The intended home for anything new is **Jeet's personal collection, id 56**.

**Open problem, found 19 August 2026:** the API key in `.env` cannot use it. The key
acts as user *Jeet, id 109, not an admin*. That account has no personal collection of
its own. Asking for collection 56 returns *403 permission denied*. So the script
cannot save there today.

**Same problem for collection 129 `Jeet Claude x Metabase`, found 20 August 2026.**
Saving there returns *403* on `/api/card`. The collection does not even show up in
`GET /api/collection` for this key, so the key cannot read it either. `GET
/api/collection` returns exactly four rows: `root`, 3, 70, 134. One API key issued from
an account that can see 129 fixes both this and the collection 56 case.

Until that is fixed:

- **Ask before saving anything.** Never pick a collection without confirming.
- The options that work with this key are `root`, `70`, and `134`, and none of them is
  a private space.
- The clean fix is an API key issued from the account that owns collection 56. A
  second option is a sub-folder under `root` named for this work.

## Naming a saved question

`[<area>] <what it answers> (<date range if fixed>)` — for example
`[Documents] Created by type, last 7 days`. Put the question it answers and the date
it was verified in the description.
