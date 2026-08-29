# courier

The centralized communication and notification gateway for Refrens. Routes all outgoing messages — transactional email, WhatsApp, Slack, and mobile push — mapping system events to templates and dispatching them through the appropriate provider.

**Tech:** Feathers v4 (Express), MongoDB (Mongoose), AWS SES, MJML, Handlebars, Node.js
**Tags:** backend, backend-core, full-stack

## What it contains

- Multi-channel dispatch hooks in `src/hooks/` (send-email, send-whatsapp) that map events to templates and channels.
- 150+ email/notification templates in `src/templates/` authored with MJML (responsive layout) and Handlebars (variable injection).
- Provider helpers in `src/helpers/` for Google Gmail, Microsoft Graph/Outlook, AWS SES, plus SuprSend and Slack integrations in `src/lib/`.
- Mailer, Transport, and Events Feathers services in `src/services/`, with Mongoose models tracking communication status (Sent, Failed, Opened).
- CLI tasks for scheduled notifications and vault tooling under `src/commands/`.

## When to reach for it

- Authoring or editing an email/notification template (MJML/Handlebars).
- Adding a new communication channel or wiring up a new provider (SES, Gmail, Outlook, Slack, SuprSend, push).
- Changing how system events map to notification templates and channels.
- Debugging email/WhatsApp delivery, bounce/complaint handling, or notification status tracking.
