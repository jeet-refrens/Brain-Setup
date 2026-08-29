# andromeda

Meta-repo for the Refrens engineering setup. `andromeda` tracks all Refrens repositories in
one place and clones them in as separate git repos (it is **not** a monorepo). Repos are
managed with [`mani`](https://manicli.com) and selected by tag.

> Already set up? See [CLAUDE.md](CLAUDE.md) for how to use andromeda (repo map, `mani`
> commands, workflow). This README is about **setup**.

## Setup

### 1. Clone andromeda

```bash
git clone git@github.com:refrens/andromeda.git
cd andromeda
```

### 2. Install dependencies

One command — installs `mani`, `just`, `worktrunk`, and `bun`, then clones all repos:

```bash
just setup
```

- **macOS** — uses [`Brewfile`](Brewfile) (`brew bundle`). Requires [Homebrew](https://brew.sh).
- **Linux** (glibc distros) — [`scripts/setup-linux.sh`](scripts/setup-linux.sh) installs
  Homebrew if missing, then runs the same `brew bundle`.

MongoDB isn't installed by `just setup` — run the datastores via Docker (below).

Don't have `just` yet? Install it first (`brew install just`, or see
[just.systems](https://just.systems)), then run `just setup`.

### 3. Get the repos

`just setup` already runs `mani sync`. To re-sync or pull a subset later:

```bash
mani sync                      # clone/update all repos
mani sync --tags frontend-web  # only a tagged subset
just sync packages             # shortcut
```

Repos are cloned as flat siblings of `mani.yaml` (`andromeda/serana/`, `andromeda/lydia/`, …)
and are gitignored, so they're never committed back into andromeda.

### Already have repos cloned elsewhere?

Symlink your existing clones instead of re-cloning:

```bash
just link ~/code/refrens     # or: ./bin/link-repos ~/code/refrens
```

### Start local datastores

Mongo, Elasticsearch, and Redis run via Docker:

```bash
just infra-up                # docker compose up -d (Mongo :27017, ES :9200, Redis :6379)
just infra-down              # stop them
```

## Everyday commands

```bash
just            # list all recipes
just repos      # list all repos
just tags       # list all tags
mani exec --tags backend -- git status
```

Full usage — repo map, `mani` reference, and the development workflow — is in
[CLAUDE.md](CLAUDE.md). Per-repo context is in [`docs/<repo>.md`](docs/).
