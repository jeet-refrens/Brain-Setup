# Businesses created, by day and country

**Question:** how many real businesses signed up in a date range, split by day and by
country, with internal and test accounts left out?

**Database:** 2 `refrens` (MongoDB) · **Collection:** `businesses`
**Query:** [businesses-created-by-day.json](businesses-created-by-day.json)
**Last verified:** 19 August 2026

## Run it

```bash
python scripts/mb.py run --db 2 --file docs/data/query-library/businesses-created-by-day.json --collection businesses --probe
```

Change the date in the `$match` to move the window.

## What it does

One `$match` on `createdAt`, `isRemoved` and `isHardRemoved`. Then an `$addFields`
that tags each business `isInternal` when its `urlKey` contains `test` or `demo`,
case ignored. Then a `$facet` that gives four answers in one pass over the same set:

- `totals` — real versus internal
- `byDay` — real signups per day
- `byCountry` — real signups per country
- `excludedSample` — up to 60 of the `urlKey`s that were dropped

`createdAt` and `isRemoved` are both indexed, so the opening filter is cheap.

Days are cut on **IST** (`Asia/Kolkata`), not UTC, because "today" for Refrens means
an Indian day. The start date in the `$match` is written in UTC, so an IST day starts
at `T18:30:00Z` on the day before.

## Result on 19 August 2026, for the 7 days from 13 August IST

| | Businesses |
|---|---|
| All, minus deleted | 4,045 |
| Internal or test | 33 |
| **Real signups** | **4,012** |

| Day (IST) | Businesses |
|-----------|------------|
| 2026-08-13 | 705 |
| 2026-08-14 | 616 |
| 2026-08-15 | 377 |
| 2026-08-16 | 330 |
| 2026-08-17 | 639 |
| 2026-08-18 | 678 |
| 2026-08-19 | 667 |

15 August is Independence Day in India and 16 August was a Sunday, which is why those
two days are low.

| Country | Businesses |
|---------|------------|
| IN | 2,988 |
| US | 221 |
| PK | 100 |
| MY | 96 |
| AE | 82 |
| ZA | 62 |
| SA | 38 |
| KE | 36 |
| BD | 35 |
| GB | 30 |

India is 74.5% of the week. The rest of the world is 1,024, or 25.5%. Dropping the
internal accounts barely moves that split.

About 4,000 real signups a week. Probe 199 ms, query 149 ms.

## Watch out for

- **The test filter is a plain substring match.** It reads `urlKey` only. A real
  business called something like *Contest Media* or *Demography Labs* would be
  dropped. On 19 August 2026 all 33 excluded keys were checked by eye and every one
  was genuinely internal, for example `test-cht5et`, `demo-jm4s29`,
  `refrens-test-t2q6pq`, `deco-test-business`. Read `excludedSample` before trusting
  the number.
- **It only catches test accounts that say so in the URL.** A test account with a
  normal-looking `urlKey` still counts as real.
- **The last day is partial** if you run this mid-day. Read the final row as
  "so far today".
- `country` holds two-letter ISO codes. Filter `"IN"`, never `"India"`.
