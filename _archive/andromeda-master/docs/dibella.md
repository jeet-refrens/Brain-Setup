# dibella

A serverless image and PDF generation service built on Azure Functions. Renders HTML/templates to PDF (invoices, quotations, delivery notes) and generates images (Open Graph, standard) using Puppeteer and Sharp, with auto-scaling and zero idle cost.

**Tech:** Azure Functions v4, TypeScript, Puppeteer, Sharp, Handlebars, Azure Blob Storage, AWS S3
**Tags:** backend

## What it contains

- Independent Azure Function endpoints in `src/functions/`: `pdf.ts` (general PDF), `cerespdf.ts` (PDF for Ceres), `img.ts` (image generation), and `og.ts` (Open Graph images).
- Rendering helpers in `src/helpers/`: `getBrowser.ts` (Puppeteer headless-Chrome instance management), `getPageSize.ts` (page-size calculations), and `wrap.ts` (HTML wrapping for rendering).
- Handlebars templates in `src/templates/` (business, portfolio, review) for injecting dynamic data before rendering.
- Sharp-based image post-processing (resize, crop, compress, format conversion) and output storage to Azure Blob / AWS S3.

## When to reach for it

- Changing PDF rendering for invoices, quotations, or delivery notes (HTML → PDF via Puppeteer).
- Working on image generation — Open Graph/social images or Sharp-based resizing/watermarking.
- Editing a Handlebars rendering template or page-size logic.
- Tuning serverless headless-browser management or output storage destinations.
