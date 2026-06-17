# Item 1 — Disclaimer Text (Screen + Voice)

## Builder evidence (CODE)

- `stage-3/app/data/disclaimers.v1.complete.json` — full disclaimer catalogue.
- `stage-3/app/config.py:resolve_strict` — resolver.

## Deployer evidence (capture against staging)

- [ ] Screenshot: staging Lovable UI showing the disclaimer banner on the result page.
- [ ] JSON: `GET /api/classify` response with `disclaimerText` populated (no unresolved `{{TOKENS}}`).
- [ ] Voice: QA-1 transcript showing the master disclaimer once at the start + the short-form on follow-up.
- [ ] Sign-off: get the firm to tick this row.

Status: [ ] Pending capture    [ ] Captured
