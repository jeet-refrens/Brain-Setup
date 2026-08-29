# experiments/ — spikes & exploratory work

This folder is for **exploratory / spike work, not production**. The goal is to learn something
or prove something is possible, fast.

## Rules of thumb

- **Favour speed over polish.** No tests, no error-handling, no careful abstractions required
  unless you explicitly ask for them.
- Throwaway code is fine here. Leave a short `notes.md` in each experiment saying what you were
  trying and what you found — that's the real output.
- Don't wire experiments into production paths or shared config.

## Graduating an experiment

If an experiment proves worth keeping and becomes a real feature:

1. Move it into `features/<name>/` (use `/feature-kickoff <name>` to scaffold the feature).
2. **Then** clean it up — add the spec, tests, and error-handling that production needs.

Use `/experiment-kickoff <name>` to scaffold a new experiment (`notes.md` + `prototype/`).
