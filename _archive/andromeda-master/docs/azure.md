# azure

Infrastructure-as-Code repository that defines and manages Refrens' cloud resources (primarily Azure, with some AWS and MongoDB Atlas) using Pulumi.

**Tech:** Pulumi, TypeScript, Azure, AWS, MongoDB Atlas
**Tags:** tools, devops

## What it contains

- Pulumi stacks for `dev`, `staging`, and `production` environments
- Azure App Service plans and deployment configuration
- Azure Functions configuration (used by `dibella`)
- Blob Storage accounts and access policies
- Key Vault definitions for secret management
- Virtual network, DNS, and networking/security configuration

## When to reach for it

- Provisioning or changing any Azure/AWS cloud resource (App Service, Functions, Blob Storage, Key Vault)
- Adding or rotating secrets managed through Key Vault
- Modifying networking, DNS, or environment-specific infrastructure
- Standing up infrastructure for a new service or environment
