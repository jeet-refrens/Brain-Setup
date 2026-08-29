# andromeda — Refrens engineering root

This is the **root context for all Refrens projects** and the launch point for most work —
fetch a task, scope the repos it touches, then build or fix across them. `andromeda` is a
meta-repo (not a monorepo): every Refrens repo stays independent and is cloned in here, and
most tasks span several of them. Per-repo detail lives in [`docs/<repo>.md`](docs/) — read a
repo's doc before working in it.

> Setup/installation is in [README.md](README.md). This file is about **using** andromeda.

## Finding & operating on repos with `mani`

Repos are cloned as flat siblings of this file and managed with [`mani`](https://manicli.com)
(config: [`mani.yaml`](mani.yaml)). Use `/repo-lookup` to pick repos/tags and run mani commands.

```bash
mani list projects                          # all repos and their tags
mani exec --all --parallel -- git status    # run a command across every repo
```

`mani` is for the **main checkouts** (clone, sync, pull, run across all). For **feature work**,
use worktree workspaces (below) instead.

## Feature worktrees & workspaces

Develop a feature across several repos in isolated git worktrees sharing one branch, grouped
under `.workspaces/<branch>/<repo>/`. andromeda itself stays on `master`. See the
`/create-worktree` skill for the full flow; `just --list` documents every command.

```bash
just wt REF-21949 serana courier   # create runnable worktrees for these repos on REF-21949
just test REF-21949                # run tests across the workspace
just up REF-21949                  # sync dependencies, then run serana and lydia in the foreground
```

## Repos

### Backend Services

| Repo | Purpose |
|------|---------|
| [serana](docs/serana.md) | Core backend API |
| [astrid](docs/astrid.md) | Admin / back-office API |
| [marika](docs/marika.md) | Subscription management product (customer-facing) |
| [saturn](docs/saturn.md) | Advanced accounting / bookkeeping (PostgreSQL) |
| [courier](docs/courier.md) | Email/messaging |
| [riften](docs/riften.md) | Real-time Forex rates API |
| [stella](docs/stella.md) | AI-powered service |
| [dibella](docs/dibella.md) | Serverless image/PDF generation |
| [shopifyApp](docs/shopifyApp.md) | Shopify integration |

### Frontend Apps

| Repo | Purpose |
|------|---------|
| [lydia](docs/lydia.md) | Main web app |
| [elisif](docs/elisif.md) | Public marketing / SEO pages |
| [phobos](docs/phobos.md) | Public profile pages |
| [sithis](docs/sithis.md) | Admin panel |
| [aurora](docs/aurora.md) | Mobile app (React Native / Expo) |
| [kherpa-welcome-space](docs/kherpa-welcome-space.md) | Lovable-generated Vite/React starter |
| [whiterun](docs/whiterun.md) | CMS (Strapi 3) for elisif |
| [ceres](docs/ceres.md) | Client-side Handlebars document renderer |

### UI / Component Libraries

| Repo | Purpose |
|------|---------|
| [disco](docs/disco.md) | Refrens component library |
| [jupiter](docs/jupiter.md) | Widget library (built on disco) |

### Shared Packages / Libraries

| Repo | Purpose |
|------|---------|
| [birds](docs/birds.md) | Shared helpers — Feathers hooks (backend) + utils (frontend) |
| [fence](docs/fence.md) | Config/constants library |
| [mudra](docs/mudra.md) | Number/numeric utilities |
| [talos](docs/talos.md) | Central Mongoose schema repo (~100 collections) |
| [venus](docs/venus.md) | Embeddable contact-form widget (Preact) |
| [gst-states](docs/gst-states.md) | India GST state codes data |
| [eslint-config](docs/eslint-config.md) | Shared ESLint config |

### Tools & Infrastructure

| Repo | Purpose |
|------|---------|
| [azure](docs/azure.md) | Infrastructure as code |
| [nebula](docs/nebula.md) | Ops/devops orchestration |
| [kuiper](docs/kuiper.md) | CLI repo bootstrapper |
| [mercury](docs/mercury.md) | API docs (Retype) — legacy, see refrens-docs/api |
| [github-deploy](docs/github-deploy.md) | GitHub deployment CLI |
| [seeds](docs/seeds.md) | Data seeding, migrations & Elastic sync |
