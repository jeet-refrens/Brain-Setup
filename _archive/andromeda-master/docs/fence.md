# fence

Shared library of Refrens core business logic, domain modules, and configuration constants — the single source of truth for app-wide enums, calculation engines, and bounded-context domain rules (invoicing, accounting).

**Tech:** TypeScript/JavaScript, Jest
**Tags:** packages, backend-core, backend-ai, full-stack

## What it contains

- `src/constants/` — domain-wide constants, shared enums (status codes, event names, roles), feature flag keys, and environment variable names
- `src/logic/` — core calculation engines (taxes, totals)
- `src/modules/` — domain bounded contexts such as Invoices
- Shared configuration kept in sync across all services and frontends

## When to reach for it

- Adding or changing a shared constant, enum, feature flag, or environment variable name
- Modifying core calculation logic for taxes or totals
- Changing domain rules within a bounded context (e.g. invoicing) used across services
- Diagnosing inconsistent business-rule or config behaviour between services
