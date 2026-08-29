---
description: Delegate a task through the Fable orchestrator + Sonnet implementer subagent pair
argument-hint: <task description>
---

Route the following task through the `orchestrator` subagent — call the Agent tool with `subagent_type: "orchestrator"` specifically. Do not implement this yourself, do not use `general-purpose` or any other subagent type, and do not skip delegation because the task looks small. The whole point of this command is guaranteeing that flow runs, not picking whichever approach seems fastest.

Before dispatching, make sure the orchestrator's prompt is self-contained per its own instructions (`~/.claude/agents/orchestrator.md`) — it has no tools besides `Agent`, so if the task needs specific file locations, line numbers, or context found by exploring the repo first, gather that yourself (or delegate that gathering explicitly as the orchestrator's first task) rather than assuming it can find things on its own.

Task: $ARGUMENTS
