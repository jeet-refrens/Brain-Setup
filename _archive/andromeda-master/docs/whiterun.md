# whiterun

A Strapi-based headless CMS powering Refrens marketing content — blog posts, landing-page copy, and other non-application content, managed by the content team without engineering involvement.

**Tech:** Strapi v3, MongoDB (Mongoose), Sharp, AWS S3 / Azure Storage, JavaScript
**Tags:** frontend

## What it contains

- `api/` — Strapi content types, controllers, and services
- `admin/` — Strapi admin panel customizations
- `extensions/` — Strapi plugin extensions and extended functionality
- `config/` — environment and server configuration; `strapi.js` is the main entry
- REST and GraphQL content APIs consumed by marketing pages, with role-based content editing and Sharp image processing

## When to reach for it

- Adding or changing CMS content types, controllers, or services
- Customizing the Strapi admin panel or extending its plugins
- Working on the content APIs (REST/GraphQL) that feed marketing pages
- Adjusting content editor roles, image processing, or storage configuration
