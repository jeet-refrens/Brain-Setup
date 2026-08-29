# riften

A real-time foreign-exchange (FX) rates API. Provides current and historical currency-conversion data and pushes live rate updates to connected clients over Socket.io. Manages API-client access via App ID / Secret keys (Feathers `authentication-local` strategy) — this credential-management role is why serana's config historically referred to riften as "auth".

**Tech:** Feathers v4 (Express), MongoDB (Mongoose), Socket.io, JavaScript
**Tags:** backend

## What it contains

- Currency-conversion services exposing current and historical FX rates, backed by Mongoose models in MongoDB.
- API-client access control via App ID / Secret keys using the Feathers `authentication-local` strategy.
- A Socket.io real-time layer that broadcasts rate updates to connected clients.
- Feathers services and hooks for auth-check and request handling.

## When to reach for it

- Working on currency-conversion endpoints — current or historical FX rate data.
- Changing API-client access control (App ID / Secret key issuance and verification).
- Modifying the Socket.io layer that pushes real-time rate updates.
