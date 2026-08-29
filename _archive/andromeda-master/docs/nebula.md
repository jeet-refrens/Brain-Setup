# nebula

Ops and DevOps orchestration tooling — process management for running services plus automation scripts that integrate with GitHub and Asana.

**Tech:** Node.js, Feathers.js (v5 / Koa), TypeScript, PM2, Docker, Octokit, Asana
**Tags:** tools, devops

## What it contains

- PM2 ecosystem configs (clustering, restarts, log rotation) for all backend Node.js services
- Deployment scripts: pull, build, reload
- Health check scripts for production and staging
- Log management and rotation configuration
- Environment-specific startup configurations
- DevOps automation integrating Octokit (GitHub) and Asana

## When to reach for it

- Changing how a backend service is run, clustered, or restarted in production/staging
- Adding or editing PM2 ecosystem configs or deployment/reload scripts
- Adjusting health checks, log rotation, or startup configuration for a service
- Building DevOps automation that touches GitHub or Asana
