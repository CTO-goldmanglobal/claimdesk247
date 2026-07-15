# CD-R3 — Injury Lead-Generation / "Marketing Arm for a Law Firm" — NSW Claim-Farming Assessment

**Status:** DRAFT for Legal Head decision (internal analyst memo, not legal advice)
**Date:** 2026-07-14
**Bottom line:** The described arrangement — collecting personal-injury leads and referring them to a law firm for consideration — is the conduct NSW's two 2025 claim-farming regimes now prohibit. This is the exact "Lane 2" activity the injury firewall (IX-12) and the "zero consideration for any injury matter, ever" invariant were built to avoid. **Do not proceed without a written Legal Head opinion.**

## Key conclusion for the engineering team

**ClaimDesk 247 CANNOT handle injury cases — period.** Not as a marketing arm, not under a law firm, not for a fee. The only lawful path is:
- **Property-damage-only recovery** (Lane 1) — lawful, no claim-farming exposure
- **Injury matters** → hard-firewall to a law-firm partner with **ZERO consideration** — no per-lead fee, no retainer tied to claim flow, no solicitation of individual injured persons

The engine already implements this correctly:
- `esc-injury` fires for ANY injury mention (IX-12, fail-closed since P1-1 fix)
- Injury intakes never receive a band
- No consideration changes hands for injury-mentioning matters
- The injury firewall is the board-level invariant

**Engineering implication:** the receptionist robot must NOT collect injury leads for referral. When a customer mentions injury, the robot must:
1. Stop the intake flow immediately
2. Escalate to `esc-injury`
3. Route to a human callback (law-firm partner)
4. Record zero monetisation on the audit trail

This is already the engine's behaviour. The frontend chat must not change it.

## Statutes in play

1. **Claim Farming Practices Prohibition Act 2025 (NSW)** — Civil Liability Act injury types
2. **Motor Accident Injuries Amendment (Claim Farming Practices Prohibition) Bill 2025 (NSW)** — motor-accident/CTP injury claims

Both apply to "a person" — marketers, lead-generators, AND law practices. Being a non-lawyer or operating "under a law firm" does NOT create an exemption.

## Penalties

- Up to ~$55,000 per offence
- Law practice: cannot recover costs + professional misconduct findings
- Dishonest conduct: up to 10 years' imprisonment

*[Full memo text preserved from Claude's review — see commit history for the complete version with all sections, the three-part conduct test, penalty analysis, and open items O-1 through O-6.]*

---

*This memo confirms the IX-12 injury firewall is not just good practice — it is the legal line that keeps ClaimDesk 247 outside the claim-farming prohibition surface. The engine's current behaviour (esc-injury → no band → law-firm partner → zero consideration) is the correct and lawful posture.*
