---
name: prototype-deploy
description: Deploy a prototype to Vercel via a private GitHub repo under vaidik2412 (Vaidik's personal hobby account). Use whenever Vaidik says "deploy this", "ship this", "ship to vercel", "push to vercel", "make this live", or any variant indicating a local prototype should go from dev to a live shareable URL. Covers both first-time deployments (create new private GitHub repo under vaidik2412, link a fresh Vercel project, classify and add env vars) and redeploys (push changes to existing repo, sync any new env vars before push). Trigger instead of running raw `gh repo create` / `vercel` commands — this skill enforces three conventions Vaidik always wants applied: repo is private and under vaidik2412; git author is set to vaidik2412 locally so Vercel attributes the deploy to the hobby account; env vars containing secrets are marked Sensitive in Vercel rather than added as plain env vars.
---

# Prototype Deploy

Take a local prototype and deploy it to Vercel under the personal `vaidik2412` GitHub account. This skill enforces three conventions that matter for hobby-tier prototype deployments:

1. **The GitHub repo is always private and always under `vaidik2412`.** These prototypes are internal work-in-progress, not public artifacts. The work GitHub account is for Refrens; the personal one is where prototypes live.
2. **The git author for commits in the prototype is always `vaidik2412` with the personal email.** Vercel attributes deployments to whichever GitHub account matches the commit author — and the hobby tier is tied to the personal Vercel account, not the work one. A commit authored as the work identity will land the deploy in the wrong place or fail with a permission error.
3. **Secrets always get marked as Sensitive in Vercel.** When unsure, treat it as a secret. Sensitive values can't be re-displayed in the dashboard once added, which prevents accidental leakage during screenshares and reduces the blast radius if a Vercel session is ever compromised. Marking too aggressively costs nothing; marking too loosely is hard to undo.

## Pre-flight

Run these checks before any other work. They're fast and they catch the two failure modes that swallow the most time later (wrong account, missing CLI):

```bash
gh --version          # confirm gh CLI exists
vercel --version      # confirm vercel CLI exists
gh auth status        # must show vaidik2412 as the active account
vercel whoami         # must show the personal account, not Refrens
```

If `gh auth status` shows the wrong account is active (work account is common since it's used for Refrens daily), switch with `gh auth switch -u vaidik2412`. If `vercel whoami` shows a team scope, run `vercel switch` and pick the personal account.

If either CLI is missing, install before continuing — `brew install gh vercel` on macOS, otherwise refer Vaidik to the official install pages.

## Decide: first-time deploy or redeploy

Look at the working directory and decide:

- **`.git/` does not exist** → first-time. Treat the local files as the starting point.
- **`.git/` exists but no `origin` remote, or `origin` doesn't point to `github.com/vaidik2412/...`** → first-time. The existing local commits will form the initial push.
- **`.git/` exists and `origin` points to `github.com/vaidik2412/<repo>`** → redeploy.

Use `git remote -v` to inspect.

If Vaidik explicitly says "redeploy as a new repo" or "fresh deploy", treat as first-time regardless of the existing remote.

## First-time flow

### 1. Confirm the feature name

The repo name is the feature name, used directly. If the working directory is `lead-enrichment/`, the repo name is `lead-enrichment`. Confirm with Vaidik before creating anything — once the repo and Vercel project exist, renaming touches both sides and isn't worth the friction.

### 2. Configure git author locally

Inside the project directory:

```bash
git config --local user.name "vaidik2412"
git config --local user.email "<vaidik2412's personal email>"
```

If the email isn't already known from earlier in the conversation, ask Vaidik once — it needs to be the email tied to his `vaidik2412` GitHub account (he can verify with `gh api user/emails` if uncertain). Set both locally only — never `--global`, since that would overwrite his Refrens work identity for every repo on the machine.

### 3. Identify and classify env vars

Scan for env vars in two places:

- Files: `.env`, `.env.local`, `.env.example`, `.env.development.local`, `.env.production.local`
- Code: `process.env.X` (Node/Next.js), `import.meta.env.X` (Vite), `Deno.env.get("X")` (Deno)

Build a list of every variable referenced. For each, decide whether it's **Sensitive** or **not**, defaulting to Sensitive when unsure.

**Mark as Sensitive:**

- Names containing `KEY`, `SECRET`, `TOKEN`, `PASSWORD`, `CREDENTIAL`, `PRIVATE`
- Database / connection URLs: `DATABASE_URL`, `MONGO_URI`, `MONGODB_URL`, `REDIS_URL`, `POSTGRES_URL`, `SUPABASE_SERVICE_ROLE_KEY`
- Auth-related: `JWT_SECRET`, `NEXTAUTH_SECRET`, `SESSION_SECRET`, `COOKIE_SECRET`, anything under `OAUTH_*`
- Service API keys: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `STRIPE_SECRET_KEY`, `RESEND_API_KEY`, etc.
- Values that look like credentials regardless of name — JWTs, long random strings, anything matching `sk-...`, `pk_live_...`, `ghp_...`, `xoxb-...`, etc.

**Safe to leave as not sensitive (only when confident):**

- `NEXT_PUBLIC_*`, `VITE_*`, `REACT_APP_*` — these are embedded in the client bundle by design, so marking them Sensitive is theatre that hides them from the dashboard without actually protecting anything.
- `NODE_ENV`, `PORT`, `LOG_LEVEL`, `NEXT_TELEMETRY_DISABLED`
- Feature flags (`ENABLE_X`, `FEATURE_Y`)
- Public URLs that wouldn't compromise anything if leaked (`NEXT_PUBLIC_SITE_URL`)

When genuinely ambiguous, ask a one-line clarifying question. Example: "`SUPABASE_URL` — is this just the public project URL (not sensitive) or does it include a service role token (sensitive)?" Don't ask for every variable, only the ones a heuristic can't decide.

### 4. Initialize git and make the initial commit

```bash
git init                    # only if .git/ doesn't already exist
git add .
git commit -m "Initial prototype"
```

Before committing, make sure `.gitignore` covers `node_modules/`, `.env*` (except `.env.example`), `.next/`, `dist/`, `build/`, `.vercel/`. If the file is missing or thin, write a sensible one based on the framework — a leaked `.env` in the initial commit is the most common own-goal in this flow.

### 5. Create the private GitHub repo and push

```bash
gh repo create vaidik2412/<feature-name> --private --source=. --push
```

This single command creates the repo under `vaidik2412`, sets it private, points local `origin` at it, and pushes the initial commit.

### 6. Link to Vercel and add env vars

```bash
vercel link
```

The interactive prompt asks for scope (pick the personal account, **not** any team scope) and project name (default to the feature name). Confirm both before hitting enter — picking the wrong scope here is the single most common mistake and requires deleting the project to fix.

Then add each env var. For Vercel CLI v32 and later, the syntax is:

```bash
vercel env add <NAME> production --sensitive
vercel env add <NAME> preview --sensitive
vercel env add <NAME> development --sensitive
```

Drop `--sensitive` for non-sensitive vars. The CLI prompts for the value interactively — let Vaidik paste it when asked rather than reading from `.env` and piping, which keeps secrets out of shell history.

If the installed Vercel CLI is older than v32 and `--sensitive` isn't recognized, run `vercel env add --help` to see the current flag name (Vercel renames flags occasionally), or fall back to adding the var via the dashboard with the Sensitive checkbox.

If a variable applies to multiple environments (commonly: production + preview + development for the same value), run the three commands in sequence and paste the same value each time. Vercel doesn't have a "all environments" shortcut for env-var creation via CLI.

### 7. Trigger the production deploy

```bash
vercel --prod
```

Wait for completion, then **verify the live deployment** the same way as redeploy step 4 below (confirm the production URL actually serves this build — a green build is not proof) before reporting the URL back to Vaidik.

## Redeploy flow

The repo and Vercel project already exist. Most of the time this is just commit + push, with Vercel's GitHub integration picking up the push automatically.

### 1. Re-verify git author

```bash
git config --local user.name     # should print: vaidik2412
git config --local user.email    # should print: the personal email
```

If either is wrong (commonly because the local config was never set and git is falling back to `--global`, which is the Refrens work identity), reset both as in step 2 of the first-time flow **before committing**. Once a commit is made under the wrong identity, fixing it means rewriting history with `git commit --amend --reset-author`, which is uglier than just getting it right up front.

### 2. Check for new env vars

```bash
vercel env ls
```

Compare against the env vars referenced in the working tree (same scan as first-time step 3). Anything new needs to be added with `vercel env add` (with `--sensitive` where appropriate) **before** the push, or the deployment will build successfully but fail at runtime.

### 3. Commit and push

```bash
git add .
git commit -m "<short, concrete description of the change>"
git push
```

Vercel's GitHub integration picks up the push and starts a deployment automatically — there's no need to run `vercel --prod` separately for a redeploy. Wait briefly, then report the new deployment URL.

To watch the build in real time:

```bash
vercel logs --follow
```

### 4. Verify the live deployment (required — do not skip)

A successful build is **not** proof the live URL serves what you just changed. The deploy can succeed while the production alias still serves stale content — wrong project, wrong root/output directory, a cached build, or (the classic) the repo wired to a *different* codebase than the one you edited. Always confirm the live URL reflects this change before reporting done:

```bash
vercel ls <project>     # confirm the newest deployment is ● Ready, not Error/Building
```

Then probe the production alias itself (not the per-deploy preview URL, which may sit behind auth):

```bash
# entry point loads, and key assets resolve
curl -s -o /dev/null -w "%{http_code}\n" https://<project>.vercel.app/
curl -s https://<project>.vercel.app/ | grep -i "<title>"   # or any string unique to the new build
```

Pick at least one string or asset that is **unique to the change you just shipped** (a new heading, a renamed file, a removed old entry point) and assert it's present (or the old one absent) on the live URL — a 200 alone only proves *something* deployed, not the *right* something. If a browser preview is available, screenshot the live URL and eyeball it against local. Only after the live URL matches local should you report the deployment as done.

## Things to watch out for

- **Wrong CLI scope at `vercel link`.** If multiple Vercel teams are linked, the active scope decides where the new project is created. Always confirm `vercel whoami` reads as the personal account before running `vercel link` — fixing a project created in the wrong scope means deleting it and starting over.
- **Wrong git identity from global config.** Refrens work machines almost always have a global git identity set for work commits. Local config in the prototype repo overrides it, but only if you remember to set it. Setting it explicitly at the start of every first-time deploy is cheap insurance.
- **`.env` accidentally committed.** Re-check the `.gitignore` before the first push. If a secret has already landed in a commit, rotating the secret at the source is much faster than trying to scrub git history.
- **Sensitive flag is one-way in the dashboard.** Once a var is marked Sensitive, the value can't be re-displayed — only overwritten. If Vaidik needs to retrieve a value later, he'll have to look it up at the source (e.g., the OpenAI dashboard) and re-enter it. This is the desired behavior; just don't be surprised by it.
- **Hobby tier limits.** The personal Vercel account is on the hobby tier, which has caps (deployments per day, build minutes, function execution). For a few prototypes these limits are invisible; for very active iteration on many projects, watch for `429`s from the Vercel API or "limit exceeded" warnings during deploy.
