---
description: Football-named canonical release workflow; commit, push, and open a PR after human approval, never merge main
argument-hint: <approved release scope and optional PR notes>
---

Route the following approved release step through the `release-runner` subagent — call the Agent tool with `subagent_type: "release-runner"` specifically.

This is the canonical football-named successor to `/release-approved`.

Treat invocation of this command as human approval to package the completed scope into a PR, unless the arguments say hold, wait, do not release, or otherwise express uncertainty.

Workflow language:

- `send-to-pr`: this release workflow.
- `captains-call`: the human approval that allowed this release step.
- `clean-sheet`: the prior implementation/review state should have no unresolved actionable findings.

Release runner settings:

- Model: Sonnet
- Effort: high
- Allowed: inspect diff, run verification, commit approved scope, push branch, open PR
- Forbidden: merge to main, push directly to main/master, deploy unless separately and explicitly requested

Approved release scope: $ARGUMENTS

