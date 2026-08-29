# kuiper

Internal CLI tool that scaffolds new Refrens repositories following standard conventions, so every new service, package, or app starts consistently.

**Tech:** Node.js, Prompts (interactive CLI), YAML/JSON processing
**Tags:** tools

## What it contains

- Interactive prompts to configure a new service, package, or app
- Boilerplate generation: `package.json`, ESLint config (extending `eslint-config`), `tsconfig`, README templates
- GitHub Actions CI workflow generation
- Standard dependency injection based on repo type (backend / frontend / package)

## When to reach for it

- Changing the boilerplate or conventions applied when bootstrapping a new repo
- Updating the generated ESLint/TypeScript config or CI workflow templates
- Adding a new repo type or adjusting its default dependency set
- Modifying the interactive scaffolding prompts
