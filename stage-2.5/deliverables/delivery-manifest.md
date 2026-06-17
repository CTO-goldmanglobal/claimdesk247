# Builder Self-Audit + Delivery Manifest — Stage 2.5
**Project:** AI Legal Receptionist + Accident Intake System
**Builder:** Cursor + MiniMax M3
**Delivery date:** 2026-06-13
**Audit model:** test-based (Gates G-41..G-49) — see `deliverables/test-report.txt`
**Contracts consumed:** `stage-3/app/` (engine, state machine, pdf_gen, intake_brief, dashboard, auth, audit), `architecture/LOVABLE-BUILD-CONTRACT.md`

## Delivery header
- **Stage:** 2.5 (Engine-as-Endpoint — thin HTTP wrapper for Lovable + weblink tests)
- **Spec version built against:** rule-tree v3.0.0 (Stage 3), disclaimers v1, pdf-summary v1
- **Builder run ref:** `stage-2.5/tests/run_acceptance.py` (single combined runner; local + weblink)
- **Test report:** `deliverables/test-report.txt` — `TOTAL: 16 PASS: 16 FAIL: 0` (Stage 2.5) + `30/30` (Stage 2) + `27/27` (Stage 3) = 73/73 green

## 1. Gate self-check (G-41 .. G-49)
Full table in `deliverables/traceability.md`. Quick summary:

| Gate | Pass |
|------|------|
| G-41 (HTTP parity with engine)        | Y |
| G-42 (disclaimer resolved + enum fail-closed) | Y |
| G-43 (escalation short-circuits over HTTP) | Y |
| G-44 (no PII in URL/query)            | Y |
| G-45 (brief role-gated server-side)   | Y |
| G-46 (x-test-mode env-gated)          | Y |
| G-47 (healthz returns versions)       | Y |
| G-48 (Stage 2 + Stage 3 regression)   | Y |
| G-49 (CORS allow-list, no wildcard)   | Y |

## 2. Traceability matrix
Attached: `deliverables/traceability.md`

## 3. Automated test report (Stage 2+)
```
TOTAL: 16  PASS: 16  FAIL: 0
```
Full report: `deliverables/test-report.txt`

Stage 2 regression: `30/30 green` (via T-25-016 subprocess)
Stage 3 regression: `27/27 green` (via T-25-016 subprocess)

## 4. Known gaps
1. **Stub auth** — `/api/brief` accepts `?as_email=...` (Stage 2.5 stub). Stage 4 wires a real OIDC/SAML provider; the `require_role` server-side check is the same in either mode.
2. **In-memory store** — sessions live in process memory. Restart wipes them. Stage 4 swaps for a Supabase adapter behind the same `SessionStore` Protocol.
3. **No real deployment** — the wrapper is local-only. The weblink runner (`BASE_URL=...`) is the deploy target; deployment to Vercel `syd1` is Stage 4 work.
4. **Engine-only fields passthrough is silent** — `/api/slot` accepts any unknown slot name and stores it in the intake. This is intentional (so the engine can read scenario-specific data like `simultaneous_entry`, `sight_lines`, `chain_count`, `inject_band`) but the API doesn't validate these. A real Lovable build should never send these — they're test/operator-only. Recommend documenting this in the Lovable contract.

## 5. Change requests raised this stage (CR-5)
- **CR-5-01** — *Add an explicit `/api/intake/extras` endpoint for engine-only fields.* The current passthrough is convenient for tests but muddies the contract. A separate route (e.g. `POST /api/intake/:ref/extras { fields: {...} }`) would let Lovable's client pass scenario data explicitly without confusing the `/api/slot` spec-slot contract. Defer to Stage 4 unless Lovable's UX needs it sooner.
- **CR-5-02** — *The Lovable Build Contract specifies the wildcard `https://*.lovable.app`. The current CORS regex requires a label prefix (`preview--abc123` matches but `app` alone wouldn't).* Suggest a final regex with explicit allowed labels (`preview--`, `staging--`, plus bare `app`) at deploy time. Not a security risk — just a DX detail.
- **CR-5-03** — *No rate limiting on `/api/session` / `/api/slot`.* A misbehaving client could create unbounded sessions. Vercel Edge can rate-limit; the FastAPI app should at minimum add a per-IP cap on session creation. Stage 4.

## 6. Compliance quick-scan (legal-domain hard checks)
- [x] No numeric fault % applied to the user anywhere (the wrapper does not author output; the engine doesn't either, per Stage 2)
- [x] Master disclaimer attaches to every fault-information output (returned pre-resolved in `/api/classify`)
- [x] All 7 escalation triggers reachable from every intake state; escalation is terminal (G-19/G-43)
- [x] Injury asked before any fault output (consent → state machine S1 → S3 → S4)
- [x] Corrected rule citations only (r72, r73, r296) — engine unchanged
- [x] `[FIRM-TBC]` values are tokens, none hardcoded (resolved server-side before the response leaves the API)
- [x] Privacy/recording consent precedes any PII collection (`/api/consent` is the gate)

## 7. Verification instructions

### Local
```bash
cd /Users/finn/Smash\ repair\ Engine
pip install -r requirements-dev.txt
cd stage-2.5
python3 tests/run_acceptance.py
# → TOTAL: 16  PASS: 16  FAIL: 0
```

### Against a deployed weblink (Stage 4+)
```bash
BASE_URL=https://<preview>.vercel.app python3 tests/run_acceptance.py
# → same 73/73 green, but every request is real HTTP
```

The runner is the same file in both modes. The `HTTPClient` abstraction swaps between `TestClient` (local) and `requests` (remote) based on `BASE_URL`. Healthz is checked first; the runner aborts if the deployment is down (the underlying `requests` call will raise).

### Spot-checks
```bash
# Healthz + versions
curl https://<preview>.vercel.app/healthz
# → {"status":"ok","engine_version":"1.0.0","rule_tree_version":"3.0.0","api_version":"0.2.5.0"}

# Engine parity
PYTHONPATH=stage-3 python3 -c "from app.engine import classify; print(classify({'state':'NSW','accident_type':'rear-end','user_position':'front','user_motion':'stopped','injuries':'none'}).band)"
# → likely
# ...then drive the same intake through /api/session → /api/consent → /api/slot → /api/classify and expect band: "likely".

# CORS allowed origin
curl -H "Origin: https://preview--abc123.lovable.app" -I https://<preview>.vercel.app/api/session
# → access-control-allow-origin: https://preview--abc123.lovable.app

# CORS denied origin
curl -H "Origin: https://evil.example.com" -I https://<preview>.vercel.app/api/session
# → no access-control-allow-origin
```

---
**Submitted for Fables audit. Test-based, 73/73 green across all three suites (Stage 2.5 16 + Stage 2 30 + Stage 3 27).**
