# astrid

The admin / back-office API for Refrens. A FeathersJS + Mongoose service exposing internal and administrative operations that complement the core `serana` API.

**Tech:** Feathers (Express), MongoDB (Mongoose), BullMQ, Node.js
**Tags:** backend

## What it contains

- A broad set of admin/internal Feathers services covering businesses, leads, invoices, payouts, coupons, notifications, network-search, metrics, and integrations.
- bull-board job queues (BullMQ) for background processing.
- Global hooks for cross-cutting auth, logging, validation, and job triggering.
- Third-party integration clients and admin/maintenance CLI commands.

## When to reach for it

- Adding or modifying an admin/internal service (businesses, leads, invoices, payouts, coupons, notifications, metrics, etc.).
- Working on back-office job queues (bull-board / BullMQ).
- Changing global hooks (auth, logging, validation) across astrid's services.
- Wiring third-party integrations or admin CLI commands.
