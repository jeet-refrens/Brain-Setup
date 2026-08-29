---
name: create-worktree
description: Use this skill when starting development on a Refrens feature that spans one or more repos and you need isolated worktrees to work in. Trigger when the user says "set up worktrees", "create a workspace", "start a feature", "branch serana and courier", "spin up worktrees for REF-xxxx", or when about to make changes across multiple Refrens repos and wants them isolated from the main checkouts. Also trigger when running tests/lint/diff/status across a feature's repos, starting the dev servers for a workspace, checking service ports, or tearing a feature's worktrees down. Covers `just wt`, the cross-repo verbs (test/lint/diff/status/exec/ports/port/start), and `just rm`. Sits before `refrens-git-workflow` (which handles commit/PR); this skill handles workspace setup.
---

# Refrens Worktree Workspace

Sets up and operates isolated, runnable git worktrees for a Refrens feature that touches one
or more repos — all sharing one feature branch — grouped in a single workspace folder under
andromeda. Built on `just` (front door) + `worktrunk` (`wt`, the per-repo engine).

A **workspace** is `<andromeda>/.workspaces/<branch>/<repo>/` — every repo you branched for a
feature lives here, on the same branch. The branch name *is* the workspace identity. andromeda
itself stays on `master`; you never branch it for feature work.

> Scoping which repos a feature touches is the `repo-lookup` skill's job — use it first if the
> repo set isn't obvious. Committing and raising PRs is `refrens-git-workflow`'s job — use it
> after the code is done.

---

## Step 1: Decide the branch name and repos

- **Branch**: Refrens branches are `REF-{value}` (from the Asana REF field). For a feature that
  spans repos, use the **same branch name in every repo** — that's what groups them. If the REF
  is unknown, ask; don't invent one (same rule as `refrens-git-workflow`).
- **Repos**: name them explicitly, or pass a mani tag to branch a whole group. If unsure which
  repos a task touches, invoke `repo-lookup` first.

## Step 2: Create the workspace

Run from anywhere inside andromeda (main checkout or a worktree):

```bash
just wt REF-21949 serana courier        # explicit repos
just wt REF-21949 backend-core          # or a single mani tag → all its repos
```

This creates a worktree per repo in parallel, each on `REF-21949`, under
`.workspaces/REF-21949/<repo>/`. For each repo, worktrunk's `pre-start` hook copies `.env` from
the main clone and installs deps; `workspace.ts` then writes that service's port + peer ports
into `.env` (see Ports below). A repo not cloned in andromeda is skipped with a note (run
`just sync` to clone it first).

First run per repo may need worktrunk hook approval; `just wt` passes `--yes` so it's
non-interactive.

## Step 3: Work across the repos

All verbs take the branch as an optional argument; omit it when you're already inside a
`.workspaces/<branch>/` directory.

```bash
just status REF-21949           # git status -sb across every repo + which repos are in it
just diff   REF-21949           # git diff across the workspace
just test   REF-21949           # npm test per repo (skips no-test stubs)
just lint   REF-21949           # npm run lint per repo
just exec   REF-21949 -- <cmd>  # run any command in every repo, e.g. -- git log -1
```

Verbs degrade gracefully: a repo missing a script is skipped (noted), and the aggregate exits
non-zero if any repo fails — so failures are visible, never masked.

## Step 4: Ports (services)

Each service gets a deterministic, collision-free port per `(service, branch)`:
`service_base + branch_offset`, where the offset (0–98) is a stable hash of the branch and the
bases are `lydia 7000, serana 7100, courier 7200`. Because every service on a branch shares the
same offset, peers find each other. After creation, `workspace.ts` rewrites each worktree's
`.env`: it sets `SERVER_PORT`, then shifts **every** `localhost:<known-base>` URL by the offset —
so the service's own `SERVER_URL` and all peer URLs (`COURIER_URL`, `SERANA_URI`,
`*_DOMAIN`, …) land on the right workspace ports in one pass.

```bash
just ports REF-21949            # list every service → port in the workspace
just port  serana REF-21949     # one service's port
```

## Step 4b: Run the services

Dev servers are **not** started at create time (keeps create fast). Start them on demand:

```bash
just start REF-21949            # runs `npm run watch` in every repo, in parallel (foreground)
```

Each service binds its workspace port (`just start` exports `SERVER_PORT`/`PORT`, which the
watch scripts honor). Ctrl-C stops them all. To run just one service, `cd` into its worktree
(`.workspaces/REF-21949/serana`) and run `npm run watch` there.

To add a new service to the scheme: add its base to `SERVICE_BASES` in `bin/workspace.ts`, and
give the repo a `.config/wt.toml` `pre-start` hook that copies `.env` and installs (see
serana/courier/lydia). `workspace.ts` writes the ports into `.env` after creation (any
`localhost:<base>` for a known service shifts automatically) — the hook does not touch ports.

## Step 5: Tear down

```bash
just rm REF-21949               # remove all worktrees in the workspace + delete the branch
```

`rm` force-removes (handles untracked `node_modules`/`.env`), prunes git metadata, and drops the
empty workspace folder. Do this after the feature is merged (commit/PR is `refrens-git-workflow`).

---

## How it fits together

- **`just`** (in andromeda's `justfile`) is the front door; recipes delegate to `bin/workspace.ts`.
- **`bin/workspace.ts`** (bun/TypeScript) orchestrates across repos, computes ports, and shells
  out to `wt`. It owns nothing repo-specific.
- **`wt` (worktrunk)** creates each worktree and runs the per-repo `pre-start` bootstrap.
- **Each repo's `.config/wt.toml`** owns its bootstrap: copy `.env` from the main clone + install.
  It does *not* touch ports — worktrunk shell-escapes hook commands, so `workspace.ts` writes the
  ports into each `.env` after creation instead.
- **`<andromeda>/.config/wt-workspace.toml`** sets the `.workspaces/<branch>/<repo>` path
  (passed to `wt` via `--config`, because worktrunk only honors `worktree-path` from user config).

Requires `bun` and `worktrunk` (both in the Brewfile; `just setup` installs them).
