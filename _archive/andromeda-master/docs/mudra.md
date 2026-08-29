# mudra

A number formatting and numeric utility library that provides consistent currency display and amount-in-words conversion, localized for Indian and international formats. Used across invoices, reports, and financial documents.

**Tech:** JavaScript, written-number, lodash
**Tags:** packages

## What it contains

- Indian number formatting (lakh/crore grouping)
- Currency formatting with symbol and locale support
- Amount-to-words conversion (e.g. `₹1,23,456` → "One Lakh Twenty-Three Thousand…")
- Rounding and precision utilities
- A simple `format()` API entry point

## When to reach for it

- Changing how amounts, currency, or numbers are formatted on documents or reports
- Fixing amount-in-words conversion or lakh/crore grouping
- Adjusting rounding or precision behaviour for financial values
