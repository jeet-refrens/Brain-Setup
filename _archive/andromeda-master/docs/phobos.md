# phobos

A public profile-page app. A Next.js application that serves public user/business profile pages, deployed via Serverless.

**Tech:** Next.js, React, TypeScript, styled-components (Serverless)
**Tags:** frontend

## What it contains

- Catch-all routing (`[...slug].tsx`) and `/c/[...slug]` routes that resolve to public profile pages.
- A `profiles.json` listing of usernames.
- `serverless.yml` for deployment.
- `src/components/` and helper utilities for rendering profiles.

## When to reach for it

- Building or changing public profile-page rendering or routing.
- Updating the `profiles.json` username data.
- Working on the Serverless deployment configuration.
