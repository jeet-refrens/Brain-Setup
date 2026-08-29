---
name: refrens-git-workflow
description: Use this skill when working on Refrens tasks that involve git branching, committing, or creating pull requests. Always trigger when the user mentions branching for a task, committing changes, creating PRs, or finishing development work. Triggers on phrases like "create a branch", "commit my changes", "create PR", "raise PR", "I'm done with the code", "ready to push", or when an Asana task REF is mentioned alongside any git intent. This skill handles the full lifecycle: branch → commit → PR → Asana comment. Before starting any task always trigger this for creating proper branches. 
---

# Refrens Git Workflow

Handles the complete development lifecycle for Refrens tasks: creating branches, committing with the right format, raising PRs, cross-linking them, and updating the Asana task.

---

## Step 1: Determine the Branch Name

Branch names always follow this pattern: `REF-{value}` where `{value}` is the **REF custom field** from the Asana task (e.g., `REF-21949`).

- If the user already shared the Asana task or mentioned the REF field → use that value directly
- If the user used the `asana-task-fetcher` skill earlier in this conversation → extract the REF field from those results
- If the REF value is unknown → ask: _"What's the REF number for this task? (e.g., REF-21949)"_

Never guess or invent a REF value.

### Create/checkout the branch in each relevant repo

```bash
# In each affected repo directory
git checkout -b REF-{value}
# or if the branch already exists:
git checkout REF-{value}
```

If working across multiple repos, use `mani` from the andromeda root:

```bash
mani exec --tags {tag} -- git checkout -b REF-{value}
```

---

## Step 2: Verify the Commit Convention

Refrens repos use **commitizen with commitiquette**, which follows conventional commits (`@commitlint/config-conventional`) with **no scope required**. The format is:

```
type: short description
```

Common types: `feat`, `fix`, `chore`, `build`, `refactor`, `docs`, `style`, `test`

Verify for the specific repo before committing:

```bash
# Check for commitizen setup
cat package.json | grep -A5 '"config"'
# Check the npm commit script
cat package.json | grep '"commit"'
```

If `npm run commit` exists → use it (runs `git-cz` interactively via commitiquette).
If not → fall back to checking `commitlint.config.js` or recent `git log --oneline -10` for the pattern.

---

## Step 3: Stage and Commit

Before committing, show the user what will be included:

```bash
git status
git diff --staged   # show staged changes if already staged
```

Then ask: **"Are you ready to commit? I'll create one commit for this task in each repo."**

If the user confirms:

```bash
# Stage all relevant changes
git add -p   # or git add <specific-files> — prefer explicit file additions

# Commit using commitizen (recommended in Refrens repos)
npm run commit
# This runs git-cz interactively — fill in: type, no scope, short description
```

If commitizen is not available, commit manually following the pattern from `git log`:

```bash
git commit -m "feat: your description here"
```

**Goal: one commit per repo per task.** Avoid multiple small commits — squash or amend before pushing if needed.

---

## Step 4: Ask About Pull Requests

After committing, ask: **"Ready to create GitHub pull requests?"**

If yes, proceed to Step 5.

---

## Step 5: Check `gh` CLI

```bash
gh --version
```

If not installed:

> "Please install the GitHub CLI from https://cli.github.com/ and authenticate with `gh auth login`, then come back."

If installed but not authenticated:

```bash
gh auth status
```

---

## Step 6: Create Pull Requests

### Determine base branch

```bash
git remote show origin | grep "HEAD branch"
# Usually 'main' or 'stage' — confirm before creating the PR
```

### Push the branch

```bash
git push -u origin REF-{value}
```

### Draft a detailed PR description

The description should include:

- **What changed**: a clear explanation of the feature or fix
- **Why**: the context or problem being solved
- **How**: implementation details (key files changed, approach taken)
- **Testing**: how to verify it works
- **Related PRs**: placeholder to fill in after all repos' PRs are created
- **Asana task**: link to the Asana task

Use this template:

```markdown
## Summary

{1-3 sentence description of what this PR does and why}

## Changes

- {key change 1}
- {key change 2}
- {key change 3}

## Implementation Notes

{Any non-obvious decisions, caveats, or things reviewers should pay attention to}

## Testing

{How to verify this works — manual steps, test commands, etc.}

## Related PRs

{Will be updated after all repos' PRs are created}

## Asana Task

{asana task URL}
```

### Create the PR

```bash
gh pr create \
  --title "REF-{value}: {task title}" \
  --body "$(cat <<'EOF'
{description from template above}
EOF
)" \
  --base {base-branch}
```

Repeat for each affected repo. Collect all PR URLs as you go.

---

## Step 7: Cross-link All PRs

Once all PRs are created, go back and update each PR's description to include links to all other PRs:

```bash
gh pr edit {pr-number} --body "$(cat <<'EOF'
{full description with Related PRs section filled in}

## Related PRs
- {repo-name}: {pr-url}
- {repo-name}: {pr-url}

## Asana Task
{asana-task-url}
EOF
)"
```

Do this for every PR so each one links to all others.

---

## Step 8: Comment on the Asana Task

After all PRs are created and cross-linked, add a comment to the Asana task. You need the task GID (the numeric ID from the task URL or from earlier in the conversation).

Build a detailed comment that includes:

- Summary of what was done
- All PR links
- Any relevant implementation notes

```bash
TASK_GID="{task-gid}"
COMMENT=$(cat <<'EOF'
PRs raised for REF-{value}:

{for each repo}
- **{repo-name}**: {pr-url}

**Summary of changes:**
{1-3 sentence description of what was implemented}

{any notable details the team should know}
EOF
)

curl --silent --request POST \
  "https://app.asana.com/api/1.0/tasks/${TASK_GID}/stories" \
  --header "Authorization: Bearer ${ASANA_PAT}" \
  --header "Content-Type: application/json" \
  --data "{\"data\": {\"text\": $(echo "$COMMENT" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))')}}"
```

If `ASANA_PAT` is not set, tell the user:

> "Please set the `ASANA_PAT` environment variable with a Personal Access Token from https://app.asana.com/0/my-apps, then I can post the comment."

---

## Checklist

Run through this before declaring the workflow complete:

- [ ] Branch `REF-{value}` created in all affected repos
- [ ] Changes committed (one commit per repo) with conventional commit format
- [ ] PRs created in all affected repos
- [ ] Each PR's description includes links to all other PRs and the Asana task
- [ ] Asana task commented with all PR links and a summary
