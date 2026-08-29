---
description: Football-named canonical plan-first workflow; auto scout, Fable plan, then stop for human approval
argument-hint: "[--model fable|opus|sonnet|<model-id>] [--effort low|medium|high|xhigh] [--scout auto|sonnet|haiku|none] [--scout-effort auto|low|medium|high|xhigh] <task or decision to plan>"
---

Parse `$ARGUMENTS` for optional flags, run the scout pass when enabled, then route the remaining task plus scout output through the `planner` subagent.

This is the canonical football-named successor to `/plan-first`.

Supported flags:

- `--model <model>`: planner model override. Common aliases: `fable`, `opus`, `sonnet`. Full Claude model IDs are allowed if Claude Code accepts them.
- `--effort <level>`: planner effort override. Supported levels: `low`, `medium`, `high`, `xhigh`.
- `--scout <auto|model|none>`: scout behavior override. Defaults to `auto`.
- `--scout-effort <auto|level>`: scout effort override. Defaults to `auto`.

Defaults:

- Planner model: `fable`
- Planner effort: `high`
- Scout: `auto`
- Scout effort: `auto`

Workflow language:

- `tactics-board`: this planning workflow.
- `team-sheet`: concise repo/prototype context packet when context was inspected.
- `captains-call`: human approval gate.

Routing rules:

1. Strip recognized flags from the task text before sending prompts.
2. Decide scout behavior:
   - If `--scout none`, skip scouting.
   - If `--scout auto` or no scout flag is present, skip scouting only when the task already names exact files/codepaths and the implementation surface is clearly narrow.
   - In auto mode, run `plan-scout` with Sonnet medium when the task spans multiple repos, prototype-to-prod alignment, unclear ownership, or unknown files.
   - In auto mode, raise the scout to Sonnet high only for auth/permissions, money/accounting, migrations, data correctness, production incidents, cross-service writes, or security-sensitive flows.
   - If `--scout <model>` is provided, run `plan-scout` with that model.
3. When scouting runs, call the Agent tool with `subagent_type: "plan-scout"` specifically. Do not use `general-purpose`.
4. If the Agent tool exposes a per-invocation model field for the scout, pass the selected scout model there. If not, use the `plan-scout` default and include `Requested scout model: <model>; runtime model override field was unavailable` in the scout prompt.
5. If the Agent tool exposes a per-invocation effort field for the scout, pass the selected scout effort there. If not, do not invent an unsupported field; include `Requested scout effort: <level>; runtime effort override field was unavailable` in the scout prompt.
6. Call the Agent tool with `subagent_type: "planner"` specifically. Do not use `general-purpose`.
7. If the Agent tool exposes a per-invocation model field for the planner, pass the selected planner model there. Claude Code supports this in current builds.
8. If the Agent tool exposes a per-invocation effort field for the planner, pass the selected planner effort there. If it does not, do not invent an unsupported field; call `planner` normally and include `Requested planner effort: <level>; runtime effort override field was unavailable` in the planner prompt.
9. Do not implement, do not edit files, do not delegate to an implementer, and do not start orchestration. The output of this command is a plan for the human to approve or revise.
10. The planner must include the selected planner/scout settings in its `Planner settings` section and end with a clear `captains-call` human approval gate.

Scout prompt:

Workflow: `tactics-board`.
Selected scout model: `<resolved scout model, usually sonnet>`.
Selected scout effort: `<resolved scout effort, usually medium or high>`.

Produce a `team-sheet` only. Do not plan or implement. Optimize for useful compression, not an artificial file-count limit: include all materially relevant repo areas, but group related files, cite paths/line refs instead of pasting code, and avoid exhaustive file dumps.

Task: `<arguments after removing recognized flags>`

Planner prompt:

Workflow: `tactics-board`.
Selected planner model: `<parsed --model or fable>`.
Selected planner effort: `<parsed --effort or high>`.
Selected scout behavior: `<auto|none|explicit model>`.
Selected scout model: `<resolved scout model or none>`.
Selected scout effort: `<resolved scout effort or none>`.
Scout output: `<team-sheet from plan-scout, or "Scout skipped: <reason>">`.

Use the `team-sheet` as context. Do not re-scout by default; only inspect additional files if the scout packet is missing, contradictory, or too shallow for a reliable plan. End the complete plan with a `captains-call` approval gate.

Task: `<arguments after removing recognized flags>`
