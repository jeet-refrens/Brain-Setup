# elisif

A public-facing Next.js site serving Refrens' marketing/SEO and account-entry pages — about-us, product comparisons, and auth flows (login, register, magiclink, forgot-password). Uses locale-prefixed slug routing for i18n; page content is managed in the `whiterun` (Strapi) CMS.

**Tech:** Next.js, React, TypeScript, styled-components
**Tags:** frontend, frontend-web

## What it contains

- `src/pages/` — public marketing/SEO pages (aboutus, product-comparison) and auth-entry pages (login, register, magiclink, forgotpassword), with locale-prefixed slug routing for i18n.
- `src/components/` — modular UI built on the Refrens design system.
- Integration with `whiterun` (Strapi) as the CMS source for page content.
- Shared internal libraries (e.g. `birds`, `disco`, `fence`, `jupiter`, `venus`) and the same `serana`/`riften` APIs as `lydia`, where present.

## When to reach for it

- Building or changing public marketing/SEO pages or product-comparison content.
- Working on account-entry/auth pages (login, register, magiclink, forgot-password).
- Adjusting locale-prefixed slug routing / i18n.
- Wiring page content from the `whiterun` CMS.
