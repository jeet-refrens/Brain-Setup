# github-deploy

CLI tool for creating and managing GitHub deployments via the GitHub Deployments API, giving a unified way to deploy any Refrens repo to an environment without the GitHub UI.

**Tech:** Node.js, Octokit (GitHub API), Commander (CLI)
**Tags:** tools

## What it contains

- Creation of GitHub deployment records with environment and ref
- Repository dispatch events to trigger CI/CD workflows
- Deployment status and history querying
- Support for multi-repo deployments in sequence or parallel
- `index.js` CLI entry point (run with `--help`)

## When to reach for it

- Changing how deployments are triggered or recorded against GitHub
- Adding support for a new environment or repo in the deploy flow
- Adjusting repository dispatch / CI-trigger behavior
- Modifying deployment status reporting or multi-repo orchestration
