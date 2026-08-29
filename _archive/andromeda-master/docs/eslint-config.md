# eslint-config

The centralised ESLint, Prettier, and Commitlint configuration consumed by every Refrens repo, ensuring consistent code style and catching common bugs without per-repo config drift.

**Tech:** ESLint, Prettier, Commitlint, Husky, TypeScript
**Tags:** packages

## What it contains

- `@refrens/eslint-config` — base Node.js / TypeScript rules
- `@refrens/eslint-config/react` — React + JSX rules
- `@refrens/eslint-config/react-native` — React Native specific rules
- Shared Prettier formatting and Commitlint commit-message rules (with Husky hooks)

## When to reach for it

- Changing a shared lint, formatting, or commit-message rule that applies across all repos
- Adding or adjusting an environment-specific config (Node, React, React Native)
- Resolving lint-rule conflicts or drift reported by consuming repos
