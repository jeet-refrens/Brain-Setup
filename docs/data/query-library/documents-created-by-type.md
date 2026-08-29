# Documents created, by type

**Question:** how many business documents of each type were created in a date range?

**Database:** 2 `refrens` (MongoDB) · **Collection:** `invoices`
**Query:** [documents-created-by-type.json](documents-created-by-type.json)
**Last verified:** 19 August 2026

## Run it

```bash
python scripts/mb.py run --db 2 --file docs/data/query-library/documents-created-by-type.json --collection invoices --probe
```

Change the date in the `$match` to move the window.

## What it does

The `invoices` collection holds **every** document type, not just invoices, so
grouping by `billType` gives the whole spread in one pass. It filters on `createdAt`
and `isRemoved`, both of which are indexed, so the opening filter is cheap.

## Result on 19 August 2026, for the 7 days from 12 August

| Type | Documents |
|------|-----------|
| INVOICE | 71,220 |
| QUOTATION | 20,967 |
| CREDITNOTE | 10,059 |
| PROFORMAINV | 5,175 |
| DELIVERYCHALLAN | 2,977 |
| PURCHASEORDER | 2,306 |
| SALESORDER | 609 |
| DEBITNOTE | 91 |
| PAYMENTRECEIPT | 90 |

About 113,500 documents in a week. Roughly 400 ms.

## Watch out for

- **This counts creation, not business activity.** `createdAt` is when the record was
  made. `invoiceDate` is what the user typed, and can be backdated. Use `invoiceDate`
  if the question is about the business's own timeline.
- **Sales and purchases are mixed.** `isExpenditure` separates money out from money
  in. Add it to the `$match` or the `$group` if the question needs the split.
- **Test and internal accounts are included.** Nothing here excludes them.
- **All countries are included.** There is no `country` on the document. Splitting
  India from the rest means a second query against `businesses`, then matching ids.
  See [../join-map.md](../join-map.md).
- `isHardRemoved` is not filtered. Only `isRemoved` is.
