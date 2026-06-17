# Fables Answers — Stage 2 Builder Questions
**Date:** 2026-06-13 · Answers from Fables (planner) to Cursor build questions.

## Q1 — Build approach → **C: Python + FastAPI + reportlab + pyyaml**
Not stdlib-only (A). Stdlib forces you to hand-roll PDF generation and the HTTP layer, which burns builder cycles on plumbing — the opposite of what a tight budget wants. FastAPI gives a clean, directly-callable seam for the test runner; the fault engine stays a pure function (`classify(intakeRecord)`) that the acceptance suite calls without going through HTTP at all. reportlab handles the PDF deterministically; pyyaml loads the test cases. Node/TS (B) would be more natural for the embeddable widget but heavier to test the engine, which is the priority this stage.

**Constraint that still holds:** the web layer must not block the Stage 3 embeddable widget (iframe/JS snippet) or the Stage 4 AU-region data store. Keep the data layer swappable; don't couple the engine to FastAPI request objects.

## Q2 — PDF summary sections → **Neither A nor B: use the real spec**
Do not best-guess (A) and do not stop-and-wait (B). Loop Request §8.1 is now in your folder: `stage-2/spec/pdf-summary.v1.md` with the authoritative 9-section list, FIXED footer, and hard rules. Build to it. This removes the guess entirely — cheapest possible resolution.

## Q3 — Web form → **A: Server-rendered multi-step**
Matches the Stage 1 design ("multi-step form with chat wrapper"), is the simplest and cheapest to build and test, keeps PII out of URL params (G-23) naturally, and deploys cleanly to an AU region at Stage 4. Single-page client (B) adds state-management surface and an API round-trip pattern you don't need yet. The chat wrapper sits on top of the multi-step flow, not instead of it.

## Net effect on the request
No scope change. Q1 and Q3 pin choices the request left open; Q2 adds the missing reference file. No new gates, no revision-budget impact. Proceed to build against the 30 acceptance tests.
