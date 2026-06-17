# Fables Audit — Stage 2
**Date:** 2026-06-13 · **Auditor:** Fables · **Spec versions:** rule-tree v2, disclaimers v1
**Delivery:** stage-2/app + tests + deliverables/ · manifest present, 30/30 self-reported

## Decision: **LOOP CLOSED (PASS)** — 1 minor carry-forward (F-2) + 3 CRs ruled on

Re-run and spot-check confirm the build. One cosmetic residue from CR-2-01 found; non-blocking, folded into Stage 3.

## Independent verification (Fables re-ran, did not trust manifest)

| Check | Result | Evidence |
|---|---|---|
| Acceptance suite | **30/30 PASS** | Re-ran `tests/run_acceptance.py` myself |
| Determinism (G-15) | PASS | 3 consecutive runs, identical 30/30 |
| CR-2-01 — outputs enum clean | PASS | All 6 scenarios' `outputs[].band` ∈ {likely,possible,unclear,insufficient}; v2 declared `2.0.0` |
| G-16 fail-closed | PASS | `EngineBandError` raised on out-of-enum band; `T-2-027` exercises injection |
| G-17 no % (engine + PDF) | PASS | 0 percentage matches in band outputs; **0 in rendered PDF** |
| G-18 disclaimer resolve | PASS | Generated PDF contains master string, 0 unresolved `{{...}}` tokens |
| G-19/G-20 escalation | PASS | chain≥3 → engine returns no band (escalated before band logic); serious injury escalates pre-fault |
| G-21 state scope | PASS | covered by `T-2-028` |
| G-22 consent gate | PASS | `T-2-029` persists nothing on decline |
| G-23 no PII in URL | PASS | route audit: only `{reference}`/slot-id path params, no name/rego/licence/phone in URLs |
| G-24 PDF 9 sections + footer | PASS | footer verbatim present, master disclaimer present |
| G-27 spec-version match | PASS | engine consumes v2; manifest declares versions |
| Store swappable (G-23/Stage 4) | PASS | `SessionStore` Protocol + `InMemoryStore`; data layer not coupled to engine |

**10% spot-check (3 cases by hand):** s1 canonical → `likely`; chain≥3 → escalated/no band; PDF rendered → clean. Matches expectations.

## Finding F-2 (minor / cosmetic) — carry forward to Stage 3
`rule-tree.nsw.v2.json` line ~230: `s6.band_logic` still contains a routing annotation tagged `"band": "n/a_esc_routed"`. The **emitted** outputs are clean (CR-2-01 satisfied where it matters) and the engine fails closed if that value ever reached output, so there is no runtime or compliance risk. But an out-of-enum string lingering in structured data is the exact class of issue CR-2-01 set out to remove.

**Required fix (Stage 3 kickoff, no separate cycle):** in `s6.band_logic`, replace the `n/a_esc_routed` entry with a routing flag that carries no `band` key (e.g. `{ "when": "chain_count >= 3", "route": "esc-multiparty", "pre_band": true }`). Logged as `CR-3-04`. Trivial; batched per Operating Rules §6.

## CRs raised by builder — Fables rulings

| CR | Builder request | Ruling |
|---|---|---|
| CR-3-01 | accident_type enum: map `parking` → reversing | **ACCEPT.** Car-park collisions are handled as the s5 reversing exception. Map `parking` → scenario `s5-reversing` with `location: car_park` set. Document in Stage 3 intake spec. |
| CR-3-02 | enumerate damage-location values | **ACCEPT.** Fix to `front \| rear \| left \| right \| multiple` (matches conversation-flow slot 7). No free text. |
| CR-3-03 | document `inject_band` testability hook | **ACCEPT.** Add to engine docstring + Stage 3 handoff notes; it's the seam `T-2-027` uses — keep it. |

All three are accepted and roll into the Stage 3 request. None affects Stage 2 closure.

## Loop status
Stage 2 closed in one audit, no revision cycle. Manifest was accurate; the only gap (F-2) is cosmetic and the builder's own CR list was honest. 30 tests now form the regression baseline — Stage 3 must keep them green. Carry into Stage 3: CR-3-01..04.
