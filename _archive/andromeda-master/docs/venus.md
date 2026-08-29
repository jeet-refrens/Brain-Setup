# venus

An embeddable Preact contact-form / lead-capture widget — the "Refrens Embedable Contact Form". Exports `renderFormInline` and `renderFormPopup` and ships both as a CDN/browser bundle (`dist/venus.browser.js`) and an npm package, so a contact form can be dropped into any site.

**Tech:** Preact, TypeScript, Rollup
**Tags:** packages

## What it contains

- A Preact app rendering the contact form, with `renderFormInline` and `renderFormPopup` entry points for inline and popup embedding.
- Schema/validation for the form's fields.
- A Rollup build producing the CDN/browser bundle (`dist/venus.browser.js`) plus an npm package.

## When to reach for it

- Changing how the contact form renders inline or as a popup.
- Adjusting form-field schema or validation.
- Updating the CDN/browser bundle or npm package build.
