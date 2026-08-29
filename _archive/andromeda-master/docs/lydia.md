# lydia

The flagship Refrens web application — the primary customer-facing UI covering the full document lifecycle (invoices, quotations, purchase orders, expenses, contacts, and reports).

**Tech:** Next.js, TypeScript, MobX, Socket.io, Konva, Styled Components, Formik + Yup, Vitest
**Tags:** frontend, frontend-web, full-stack

## What it contains

- `src/pages/` — Next.js file-based routing; `_app.tsx` is the global app wrapper and `index.tsx` the home page
- `src/modules/` — domain-specific feature logic (invoicing, CRM, etc.)
- `src/stores/` — MobX state stores for predictable global state management
- `src/components/` — shared React UI components used across the app
- Canvas-based document customisation powered by Konva, plus real-time collaboration over Socket.io (via `riften`)
- Consumes shared libraries: `birds`, `disco`, `fence`, `jupiter`, `mudra`, and talks to `serana`/`riften` over Axios/Feathers client

## When to reach for it

- Changing the main customer web UI for invoices, quotations, POs, credit notes, expenses, or reports
- Adding or modifying MobX stores, domain modules, or shared components in the primary app
- Working on the Konva canvas document editor or real-time Socket.io collaboration features
- Wiring new `serana`/`riften` API integrations into the flagship web experience
