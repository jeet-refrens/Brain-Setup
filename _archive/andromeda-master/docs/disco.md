# disco

Refrens' primary React component library and design system, providing branded, consistent UI components consumed by all web frontends. Storybook serves as the living style guide.

**Tech:** React 18, TypeScript, Styled Components, Storybook, Rollup
**Tags:** packages, frontend-web, full-stack

## What it contains

- `src/components/` — the full suite of core UI components (buttons, inputs, forms, tables, modals) following Refrens design tokens
- `src/icons/` — the custom Refrens icon set and icon management
- `src/theme/` — Styled Components theme definitions and design tokens
- TypeScript prop types for every component
- Storybook for isolated component development and documentation

## When to reach for it

- Adding, changing, or fixing a shared UI component used across web apps (buttons, forms, tables, modals)
- Updating design tokens, theme values, or the icon set platform-wide
- Changing a component's prop API or its Storybook documentation
- Diagnosing why a shared component renders or behaves inconsistently across consuming apps
