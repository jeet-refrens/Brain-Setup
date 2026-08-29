---
description: Football-named canonical approved execution workflow; Opus orchestrator, optional Luna scout, Terra implementation, Sol review, then stop for release approval
argument-hint: <approved plan or approved task scope>
---

Route the following approved work through the `orchestrator-opus` subagent — call the Agent tool with `subagent_type: "orchestrator-opus"` specifically.

This is the canonical football-named successor to `/execute-approved`.

Do not implement this yourself, do not use `general-purpose`, and do not skip delegation because the task looks small. This command is only for work the human has already approved.

Workflow language:

- `kickoff-approved`: this approved execution workflow.
- `var-check`: read-only adversarial review.
- `extra-time`: focused fix loop when review finds actionable issues.
- `clean-sheet`: no actionable findings remain.
- `captains-call`: human approve/hold gate before release.

Flow:

1. Orchestrator: `orchestrator-opus`, medium effort.
2. Optional scout: `codex-scout` using Codex GPT-5.6 Luna, low effort, read-only.
3. Implementer: `implementer-codex` using Codex GPT-5.6 Terra, medium effort, write-capable.
4. Reviewer: `codex-reviewer` using Codex GPT-5.6 Sol, high effort, read-only.
5. Changes loop: actionable review findings route back to `implementer-codex`, then back to `codex-reviewer`.
6. Stop for `captains-call`. Do not commit, push, open PR, deploy, or merge.

Approved work: $ARGUMENTS
