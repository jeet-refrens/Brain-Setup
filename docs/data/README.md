# docs/data/ — asking Refrens data questions

Ask a question in plain English. Get a real answer. You should not have to name a
database, a collection, a field, or a join.

Read this first.

## The idea

Two problems make data questions painful here:

1. **Nobody can remember the fields.** The main database has 118 collections and
   13,722 field paths. `invoices` alone has 1,169. Guessing a field name is the most
   common way to get a wrong answer that looks right.
2. **A careless query hurts the server.** These are production databases. One
   unfiltered scan of a big collection is a real incident.

So: field names are never remembered, they are **looked up** from a local index.
And queries are never run by hand, they go through **`scripts/mb.py`**, which
refuses the dangerous shapes.

## The loop

When you get a data question:

1. **Work out which database.** See [metabase-map.md](metabase-map.md).
2. **Look up every field you plan to use.** `python scripts/mb.py fields <db> <table> <pattern>`.
   If a field is not in the index, **stop and ask**. Never guess a name because it
   sounds right.
3. **Check what is already known.** [verified/](verified/) holds confirmed fields and
   enum values. [join-map.md](join-map.md) holds how records link.
   [query-library/](query-library/) may already answer something close.
   `python scripts/mb.py cards "<search>"` searches the 3,858 saved questions in
   Metabase, read only.
4. **Write the query to a file**, then `python scripts/mb.py check ...`.
   Fix whatever it blocks. Do not use `--override` without a stated reason.
5. **Probe, then run.** `python scripts/mb.py run ... --probe` counts the matched
   documents first, so you see the cost before the real query runs.
6. **Answer in plain language.** Numbers plus what they mean.
7. **Write down what you learned.** New confirmed fields go in [verified/](verified/).
   New links go in [join-map.md](join-map.md). A reusable query goes in
   [query-library/](query-library/). A mistake or surprise goes in
   [learnings.md](learnings.md).

Step 7 is the part that makes tomorrow cheaper than today. Do not skip it.

## Saving a question in Metabase

Only when you ask for it, and **only after confirming where it should go**.
See the "Where saved questions go" section of [metabase-map.md](metabase-map.md) —
there is an open permission problem there.

Existing saved questions are **read only**. Nothing here edits or deletes them.

## The files

| File | What it holds |
|------|---------------|
| [metabase-map.md](metabase-map.md) | Which database is which, and where saved questions go |
| [join-map.md](join-map.md) | How records link to each other, confirmed only |
| [guardrails.md](guardrails.md) | The safety rules, and which ones the script enforces |
| [verified/](verified/) | Confirmed fields, enum values and traps, per database |
| [query-library/](query-library/) | Queries that worked, with the question they answer |
| [learnings.md](learnings.md) | Dated log of mistakes and surprises |
| `cache/` | Generated field index. Not edited by hand. Not committed. |

## Keeping it fresh

`python scripts/mb.py sync` rebuilds `cache/` from Metabase. Run it when a field you
expect is missing, or after a schema change ships. The `/mb-sync` skill does this and
then tells you what changed.

## Secrets

`scripts/mb.py` reads `METABASE_URL` and `METABASE_API_KEY` from `.env` itself.
Never print, paste, or echo their values.
