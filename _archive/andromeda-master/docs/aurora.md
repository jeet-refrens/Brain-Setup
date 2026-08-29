# aurora

The Refrens cross-platform mobile app for iOS and Android — create and share invoices, track payments, and manage contacts on the go.

**Tech:** React Native, Expo, expo-router, Jotai, TanStack Query, Styled Components / UI Kitten, Firebase, i18next
**Tags:** frontend, frontend-mobile

## What it contains

- `app/` — entry points and `expo-router` file-based navigation
- `src/screens/` — application screens mapped to business logic
- `src/services/` — API and external service integrations (auth, data persistence, communication)
- `src/hooks/` and `src/models/` — shared logic, side effects, and data models
- `src/i18n/` — internationalization setup and translations via i18next
- Jotai state, TanStack Query data fetching, Firebase push notifications/analytics; shares `disco`, `jupiter`, `venus` and connects to `serana`/`riften`

## When to reach for it

- Building or changing mobile screens, navigation, or native-facing features
- Working on push notifications, analytics, or other Firebase integrations
- Modifying mobile state (Jotai) or data fetching (TanStack Query) against `serana`/`riften`
- Adding i18n translations or mobile-specific component work
