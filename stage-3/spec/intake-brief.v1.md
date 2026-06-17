# Legal-Firm Intake Brief — Content Spec (Loop Request §8.2)
**Binding for Stage 3 (gate G-36). Resolves CR-4-03.** Authoritative field list — do not derive from the test.
Internal document, delivered to the firm's nominated inbox/system. **Never customer-facing.**

## Required fields (in order)
1. **Header** — reference number, session ID, date/time, channel (web/voice), `{{FIRM_NAME}}`.
2. **All intake fields (structured)** — every slot captured (Loop Request §5.3 / conversation-flow slots 1–14), rendered as labelled key/value, not prose.
3. **Fault classification** — matched scenario + confidence band (`likely | possible | unclear | insufficient`) + rule reference(s) (corrected citations: r126, r72/73, r114, r148/149, r296). **No numeric percentage** (G-17/G-36).
4. **Escalation flags** — any of the 7 triggers fired, with the trigger ID and the turn it fired on. Neutral wording for fraud signals (never an accusation).
5. **Evidence gaps** — checklist items outstanding (from S6), as an action list for the lawyer.
6. **Recommended action** — one of: `claim` / `dispute` / `each-bear-own` / `urgent escalation`. This is an internal triage hint, framed as such — not advice to the customer.
7. **Verbatim customer statements** — key quotes from voice/chat, attributed to turn, used for the lawyer to assess cold. Quote exactly; do not paraphrase.
8. **Tow / rental status** — what was requested, slots captured, reference numbers emitted (`{{TOW_PROVIDER_REF}}` / `{{RENTAL_PARTNER_REF}}`).

## Hard rules
- **Internal only.** Must be unreachable by the `customer` role (RLS, G-33). Generated/served only for `legal_staff` / `admin`.
- **No numeric fault %** anywhere, including "recommended action" rationale (G-36).
- Framing rules still apply to any narrative text (general-information language; no advice voice). The brief may be more direct than customer output (it's for a lawyer) but must not fabricate certainty the engine didn't produce.
- Pulls from the same audit-logged session data; no re-classification — render the band the engine already assigned.
- Plain structured layout; a lawyer should be able to assess the matter cold in under a minute.

## Test hook
`T-3-026` asserts all 8 field groups present, `customer_facing: false`, `percentage_in_brief: false`. Add a field-presence assertion for each of the 8 groups against a completed rear-end session.
