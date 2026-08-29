---
name: repo-lookup
description: Use when working in the Refrens andromeda meta-repo to figure out which repo(s) or mani tag a task touches, and to run commands across those repos with mani. Trigger before starting any Refrens task/feature/bugfix to scope the work ("which repo handles invoices/auth/payments?", "where do I add a shared validator?"), and whenever running git/npm/shell commands across multiple repos ("pull all backend repos", "build the packages", "run X in every frontend app"). Covers mani exec/run/sync/list, --tags and --tags-expr filtering, and the repo→tag map.
---

# Refrens repo lookup & mani

Refrens is a meta-repo: ~32 independent git repos managed together by
[`mani`](https://github.com/alajmo/mani) from the `andromeda` root (the directory holding
`mani.yaml`). This skill does two things:

1. **Scope** — given a task, find which repo(s) and which tag to work on.
2. **Operate** — run git/npm/shell commands across those repos with `mani`.

Repos are **flat siblings** of `mani.yaml` (`andromeda/serana/`, `andromeda/lydia/`, …).
Always run `mani` from the `andromeda` root.

## Scoping a task

1. Identify the domain: frontend, backend, shared package, or tooling.
2. Find the repo(s) — use the table below, read `docs/<repo>.md` for detail, or query live:
   ```bash
   mani list projects                 # all repos + their tags
   mani list projects --tags backend  # repos carrying a tag
   mani describe projects serana      # one repo's url, path, tags, desc
   ```
3. Pick the **narrowest tag** that covers all involved repos (don't run a backend command
   across every repo). For one or two repos, name them with `--projects` instead.

`docs/<repo>.md` (in the andromeda root) is the per-repo context — read it before working in
a repo. There is one flat file per repo (e.g. `docs/serana.md`), not a `docs/repos/` tree.

## Tags

Every repo carries a **category** tag (`backend` · `frontend` · `packages` · `tools`) plus
the **group** tags it belongs to. Tags are how you select subsets — they replaced the old
`meta` groups one-for-one (same names). This table is a quick reference; `mani list tags` is
the live source of truth.

| Tag | Repos |
|-----|-------|
| `backend` | serana, astrid, marika, saturn, courier, riften, stella, dibella, shopifyApp |
| `frontend` | lydia, elisif, phobos, sithis, aurora, kherpa-welcome-space, whiterun, ceres |
| `packages` | disco, jupiter, birds, fence, mudra, talos, venus, gst-states, eslint-config |
| `tools` | azure, nebula, kuiper, mercury, github-deploy, seeds |
| `backend-core` | serana, saturn, courier, birds, fence, talos |
| `backend-ai` | serana, stella, birds, fence |
| `frontend-web` | lydia, elisif, disco, jupiter |
| `frontend-mobile` | aurora |
| `full-stack` | serana, saturn, courier, lydia, disco, jupiter, birds, fence, talos |
| `devops` | azure, nebula |

**Choosing a tag:**
- UI only → `frontend-web` or `frontend-mobile`
- API only → `backend-core`, or `backend-ai` for AI features
- Touches both UI + API → `full-stack`
- A shared library → `packages`
- Infra / ops / deploy → `devops`
- A whole category → `backend` / `frontend` / `packages` / `tools`
- Unsure → read the per-repo docs first

## Running commands across repos

```bash
mani exec --all -- git status              # every repo  (-a / --all)
mani exec --tags <tag> -- git pull         # repos with a tag
mani exec --projects serana,lydia -- <cmd> # named repos
mani exec --all --parallel -- git fetch    # concurrently (-p / --parallel)
```

`--` separates mani flags from the command run in each repo. Common uses:

```bash
mani exec --all -- git pull
mani exec --tags packages -- npm run build
mani exec --tags frontend-web -- npm install
mani sync                                  # clone any repos in mani.yaml missing locally
```

**Boolean tag expressions** with `&&`, `||`, `!`, parentheses (`-E` / `--tags-expr`):

```bash
mani exec --tags-expr '(frontend-web || frontend-mobile) && !packages' -- git status
mani exec --tags-expr 'backend-core && !full-stack' -- npm test
```

## Tasks

Reusable commands defined under `tasks:` in `mani.yaml`, invoked with `mani run`:

```bash
mani list tasks                            # what's defined (status, pull, install, build)
mani run status --all
mani run build --tags frontend-web
```

## Common multi-repo tasks

| Task | Repos | Tag |
|------|-------|-----|
| Invoice/quotation feature end-to-end | lydia + serana | `full-stack` |
| New shared hook / validator | birds or talos | `packages` |
| New ESLint rule | eslint-config | `packages` |
| Subscription / billing flow | marika + saturn + lydia | `full-stack` |
| AI feature | stella + serana + birds | `backend-ai` |
| Mobile change | aurora | `frontend-mobile` |
| Deploy / infra change | azure + nebula | `devops` |

## Caveats

- **Shell evaluation**: expressions in `exec` are evaluated by the parent shell before
  running in each repo. To evaluate per-repo, escape: `mani exec --all -- echo \$PWD`.
- **`mani sync`** only clones repos missing locally; it won't touch existing clones' working
  trees (use `git pull` / a task to update those). Safe to re-run.
- **Run from the andromeda root** — the directory containing `mani.yaml`.
