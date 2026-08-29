# ceres

A static, client-side Handlebars document renderer. It runs in the browser, fetches its JSON data (from a Base64-encoded URL), and fills Handlebars templates to produce documents such as invoices, receipts, and reports at runtime.

**Tech:** Webpack 5, Handlebars, ES5 static (vanilla JS)
**Tags:** frontend

## What it contains

- `src/main/` — core rendering logic and entry point that fetches JSON and fills templates.
- `src/templates/` — Handlebars templates for documents (invoices, receipts, reports).
- `src/widgets/` — self-contained UI widgets.
- `src/vendor/` — third-party library integrations and shims.
- A Webpack 5 build emitting an ES5-compatible static bundle.

## When to reach for it

- Authoring or editing Handlebars templates for documents (invoices, receipts, reports).
- Changing the client-side render flow (JSON fetch from a Base64 URL, template filling).
- Building or modifying self-contained widgets.
- Changing the Webpack build that produces the static ES5 bundle.
