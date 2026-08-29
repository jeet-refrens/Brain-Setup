# talos

The central Mongoose schema repository for Refrens. Defines the full document schemas for roughly 100 (≈103) MongoDB collections — invoices, leads, businesses, clients, inventories, users, GST filings, and more — shared across the backend services. It also bundles a global `stringMaxLength` Mongoose plugin and a set of regulatory format validators.

**Tech:** TypeScript / JavaScript, Mongoose
**Tags:** packages, backend-core, full-stack

## What it contains

- Mongoose schema definitions for ~100 MongoDB collections (invoices, leads, businesses, clients, inventories, users, GST filings, …), shared across backend services.
- A global `stringMaxLength` Mongoose plugin.
- Format validators (GST, PAN, phone).

## When to reach for it

- Adding or changing a shared Mongoose document schema used across backend services.
- Updating the global `stringMaxLength` plugin.
- Adjusting regulatory/format validators (GST, PAN, phone).
