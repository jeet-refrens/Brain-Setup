---
description: Thin backwards-compatible alias for /tactics-board with Fable high
argument-hint: <task or decision to plan>
---

This is a backwards-compatible alias for `/tactics-board --model fable --effort high`.

Follow `/tactics-board` exactly with planner model `fable` and planner effort `high`. This alias exists only for muscle memory.

Use the canonical tactics-board scout behavior: `auto` unless the prompt explicitly says to skip scouting.

Do not implement, do not edit files, do not delegate to an implementer, and do not start orchestration. The output of this command is a plan for the human to approve or revise.

Task: $ARGUMENTS
