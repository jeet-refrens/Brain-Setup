# Draft — Shopify dev community post

Post this in the Products and Orders APIs board — same board as the linked thread below. When you
post, attach each file marked `[Attach: ...]`. The community editor lets you drag in images and
`.json` files directly.

---

## Title

Line-item `tax_lines` duplicated once per order line count — Fastrr checkout orders, `orders/create` webhook

## Body

We think we're hitting the `tax_lines` duplication bug described here: [Observing an unexpected
behavior in the Shopify orders/create (and orders/updated) webhook payload related to tax_lines at
the line item level](https://community.shopify.dev/t/observing-an-unexpected-behavior-in-the-shopify-orders-create-and-orders-updated-webhook-payload-related-to-tax-lines-at-the-line-item-level/33361).

Donal, from Shopify, explained the cause there. An app creates an order through the Admin REST API
(the API used to create orders by code). It sends `tax_lines` at the order level, not per line
item. Shopify then splits that total across every line item on its own.

We want to confirm this is the same cause behind what we're seeing below. We also want to know if
this is permanent, or something Shopify plans to fix. Shopify fixed a similar bug in the
Subscriptions API in Jan 2023.

**Setup**

Merchant: `hiddenapple.in`. Checkout: Fastrr. Tax: a flat 5% IGST (India's tax on sales between
states), one tax type, no CGST/SGST split, no overrides. See the attached tax settings screenshot:
`[Attach: shopify-tax-configuration.png]`.

**What we found**

For every Fastrr order, each line item's `tax_lines` array holds one entry per line item in the
whole order. This happens with no discount, a fixed discount, and a Buy-2-Get-1 discount. So the
discount type isn't the cause.

| Order | Line items in order | Duplicate `tax_lines` per line item | Discount |
|---|---|---|---|
| `#INVHA1291` | 3 | 3 | Buy-2-Get-1 (₹999) |
| `#INVHA1816` | 2 | 2 | ₹100 fixed |
| `#INVHA1777` | 2 | 2 | none |

A manual order on the same store, not through Fastrr, with the same number of line items, has
exactly **one** `tax_lines` entry per item. That's what we'd expect.

**Example**

Order `#INVHA1816` has 2 line items and a ₹100 discount. One line item's `tax_lines` field:

```json
"tax_lines": [
  { "title": "IGST", "rate": 0.05, "price": "22.60" },
  { "title": "IGST", "rate": 0.05, "price": "22.60" }
]
```

Two entries. Same title, same rate. The order has 2 line items. Full file attached:
`[Attach: order-from-fastrr-with-100-discount.json]`.

**Our questions**

1. Is this the same "order-level `tax_lines` split across line items" behaviour Donal described?
   Or is it a separate issue?
2. Is this permanent behaviour for orders created this way? Or does Shopify plan to fix it
   upstream, the way it fixed the Subscriptions API?
3. We suspect duplication could also hit CGST and SGST orders (India's two-part sales tax for
   sales within one state), not just IGST. Here's our plan to handle it — group `tax_lines`
   entries by **title and rate together**, and count each distinct title+rate combination's rate
   only once, even if it repeats:
   - Two `IGST` entries at 5% → counted as one 5% `IGST`.
   - A `CGST` entry at 2.5% and an `SGST` entry at 2.5% → still added, since the titles differ
     (2.5% + 2.5% = 5%).
   - Two entries with the same title but different rates — for example, stacked US state, county,
     and city tax — still added, since the rates differ.

   Is this the right way to handle it? Or is there a case where it would give the wrong number?

We can share full order files and invoice screenshots if that helps:
`[Attach: invoice-with-incorrect-tax.png]`, `[Attach: invoice-without-discount.png]`.
