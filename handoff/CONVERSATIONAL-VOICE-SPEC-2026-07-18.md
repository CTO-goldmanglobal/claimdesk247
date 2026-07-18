# Conversational Voice Spec — ClaimDesk 247

**Date:** 2026-07-18
**Status:** Spec for a future chat. Not building now — planning the shell + migration path.
**Scope:** Add full-duplex conversational voice to the `/intake` chat (customer talks, receptionist talks back, natural conversation flow). The free push-to-talk (browser Web Speech API) stays live as the fallback.

**Companion context:**
- `handoff/RECEPTIONIST-ROBOT-SPEC-2026-07-15.md` — the chat architecture this extends
- `handoff/PROJECT-SUMMARY-FOR-OPUS.md` — §3.1 "engine decides, LLM describes" governance
- `stage-4/legal/CD-R3-injury-lead-generation-2026-07-14.md` — the injury firewall that MUST hold in voice mode

---

## 1. The architecture (provider-agnostic shell)

The conversational voice shell is built as a **provider-agnostic abstraction** so the STT/TTS layer can be swapped without touching the engine or chat logic.

```
┌─────────────────────────────────────────────────┐
│  Browser (client-side)                          │
│                                                  │
│  ┌──────────┐  audio  ┌──────────┐  text  ┌───┐│
│  │ Mic +    │────────▶│ STT      │───────▶│   ││
│  │ WebRTC   │         │ Provider │        │ E ││
│  │ capture  │◀────────│ TTS      │◀───────│ N ││
│  │ + speaker│  audio  │ Provider │  text  │ G ││
│ └──────────┘         └──────────┘        │ I ││
│                                          │ N ││
│  ┌──────────────────────────────────────┐│ E ││
│  │ Chat state machine (existing)        ││   ││
│  │ - Drives the conversation flow       ││   ││
│  │ - Calls /api/slot, /api/classify     ││   ││
│  │ - Injury firewall enforced           ││   ││
│  └──────────────────────────────────────┘└───┘│
└─────────────────────────────────────────────────┘
```

The engine (right side) is UNCHANGED. The voice layer (middle) is a pluggable adapter. The browser (left) captures/plays audio.

---

## 2. The provider abstraction

```typescript
// src/lib/receptionist/voice-provider.ts

interface VoiceProvider {
  /** Start listening. Returns a stream of interim + final transcripts. */
  startRecognition(
    onTranscript: (text: string, isFinal: boolean) => void,
    onError: (err: string) => void,
  ): Promise<void>;

  /** Stop listening. */
  stopRecognition(): void;

  /** Speak text aloud. Returns when speech completes. */
  speak(text: string): Promise<void>;

  /** Stop any in-progress speech. */
  cancelSpeech(): void;

  /** Whether this provider is available in the current browser/env. */
  isSupported(): boolean;

  /** Human-readable name for diagnostics. */
  readonly name: string;
}
```

Three implementations, in order of cost:

### Provider 1: Browser-native (FREE — already built, the fallback)

- STT: `window.SpeechRecognition` / `webkitSpeechRecognition`
- TTS: `window.speechSynthesis`
- Cost: $0.00
- Quality: Functional but robotic TTS; good STT on Chrome, decent on Safari
- Already shipped at `src/lib/receptionist/voice.ts`

### Provider 2: Telnyx STT + browser TTS (~$0.075/5min)

- STT: Telnyx Speech-to-Text API ($0.015/min) — better accuracy, handles accents/noise
- TTS: Browser SpeechSynthesis (still free) — save the $0.0074/min
- Transport: Browser WebRTC (no Telnyx SIP needed — the browser talks directly to the Telnyx STT API over WebSocket)
- Cost: ~$0.075 per 5-min chat
- Setup: Telnyx API key in Supabase secrets

### Provider 3: Telnyx WebRTC + STT + TTS (~$0.12/5min)

- STT: Telnyx ($0.015/min)
- TTS: Telnyx ($0.0074/min) — natural voice quality
- Transport: Telnyx WebRTC SDK ($0.002/min) — full-duplex, phone-like
- Cost: ~$0.12 per 5-min chat
- Setup: Telnyx SIP connection + credential + API key + @telnyx/webrtc SDK

### Provider selection logic

```typescript
// Runtime: pick the best available provider.
// Config via VITE_VOICE_PROVIDER env var: "browser" | "telnyx-stt" | "telnyx-full"
// Default: "browser" (free, zero setup)
function getVoiceProvider(): VoiceProvider {
  const configured = import.meta.env.VITE_VOICE_PROVIDER ?? "browser";
  switch (configured) {
    case "telnyx-stt":
      return new TelnyxSTTProvider();   // needs API key
    case "telnyx-full":
      return new TelnyxWebRTCProvider(); // needs SIP + API key + SDK
    default:
      return new BrowserVoiceProvider(); // free, always available
  }
}
```

This means: start with browser-native (free, live now), flip `VITE_VOICE_PROVIDER=telnyx-stt` on Vercel when you want better STT quality (no code change), flip to `telnyx-full` when you want premium voice. The chat logic never changes.

---

## 3. The conversational flow

The key design constraint: **the engine is deterministic, not conversational.** It asks structured questions (state → claim_type → collision_type → ...). Voice doesn't change what the engine asks — it changes how the customer answers.

### The voice turn cycle

```
1. Engine asks a question (e.g. "What state did the accident happen in?")
2. TTS speaks the question aloud
3. STT starts listening
4. Customer speaks their answer (e.g. "New South Wales")
5. STT returns the transcript
6. The transcript is mapped to an engine option:
   - "new south wales" → "NSW"
   - "n s w" → "NSW"
   - "sydney" → "NSW" (location → state inference)
   - If no match → re-ask the question ("I didn't catch that. NSW or outside NSW?")
7. The mapped value is submitted to /api/slot
8. Repeat from step 1 until done → classify → result/escalation
```

Step 6 (transcript → engine enum mapping) is the tricky part. It needs a lightweight LLM or fuzzy-matching layer. Options:

### Option A: Fuzzy matching (cheapest, no LLM)

```typescript
function mapTranscriptToOption(transcript: string, options: {value: string, label: string}[]): string | null {
  const normalized = transcript.toLowerCase().trim();
  // Direct match
  for (const opt of options) {
    if (normalized === opt.value.toLowerCase() || normalized === opt.label.toLowerCase()) return opt.value;
  }
  // Contains match
  for (const opt of options) {
    if (normalized.includes(opt.value.toLowerCase()) || opt.label.toLowerCase().includes(normalized)) return opt.value;
  }
  // Common aliases (hard-coded map)
  const ALIASES: Record<string, string[]> = {
    "NSW": ["new south wales", "nsw", "sydney", "newcastle", "wollongong"],
    "outside_nsw": ["victoria", "vic", "melbourne", "queensland", "qld", "brisbane", "perth", "wa", "adelaide", "sa", "hobart", "tas", "darwin", "nt", "act", "canberra"],
  };
  for (const [value, aliases] of Object.entries(ALIASES)) {
    if (aliases.some(a => normalized.includes(a))) return value;
  }
  return null; // no match → re-ask
}
```

This works for enums (state, collision_type, claim_type) where the options are known. For free-text slots (vehicle description, narrative) the transcript goes directly into the text value — no mapping needed.

### Option B: MiniMax M3 / DeepSeek V4 Flash (cheap LLM, ~$0.001/query)

Send the transcript + the available options to a cheap LLM and ask it to pick the best match. This handles accents, paraphrasing, and edge cases better than fuzzy matching.

```
POST https://api.minimax.chat/v1/chat/completions
{
  "model": "MiniMax-M3",
  "messages": [
    {"role": "system", "content": "You map spoken text to the closest option. Reply with ONLY the value, nothing else."},
    {"role": "user", "content": `Transcript: "${transcript}"\nOptions: ${JSON.stringify(options)}\nWhich option?`}
  ],
  "max_tokens": 10,
  "temperature": 0
}
```

Cost: ~$0.001 per query (MiniMax M3) or ~$0.0002 (DeepSeek V4 Flash). At 11 questions per intake, that's ~$0.011 per chat for the LLM mapping layer. Negligible.

**Recommendation:** Start with Option A (fuzzy matching, $0). Add Option B (LLM) when fuzzy matching fails on real customer accents.

---

## 4. The UI

A toggle in the chat header: **"Voice mode"** (on/off).

When ON:
- The text input area is replaced by a large mic button (or hidden entirely)
- Each system message is spoken aloud (TTS)
- The customer speaks their answer after each question
- A small transcript preview shows what the system heard (so the customer can verify)
- The progress bar + chat history still work the same way

When OFF:
- The chat works exactly as it does today (text input, button choices, optional push-to-talk mic)

---

## 5. The injury firewall in voice mode (CD-R3 — non-negotiable)

The engine enforces the firewall server-side. In voice mode, when the engine returns `escalation: "esc-injury"`, the voice shell MUST:

1. Stop listening immediately
2. Speak the handoff message aloud: "I'm sorry to hear that. I'm going to stop our chat here and have a real person call you. Your safety and recovery come first. Your reference is GF-XXXXXXXX."
3. Show the escalation handoff panel (same as text mode)
4. NOT ask any more questions, NOT collect any injury details

This is already enforced by the existing `applyNext` escalation check + `SlotEscalationPanel`. The voice layer just needs to call `speak()` on the handoff message before rendering the panel.

---

## 6. Implementation order (future chat)

1. **Provider abstraction** — `src/lib/receptionist/voice-provider.ts` with the `VoiceProvider` interface + `BrowserVoiceProvider` (extract from existing `voice.ts`)
2. **Conversational controller** — `src/lib/receptionist/conversational-voice.ts` — the turn cycle (speak question → listen → map → submit → repeat)
3. **UI toggle** — voice mode on/off in the chat header
4. **Fuzzy matcher** — `src/lib/receptionist/transcript-mapper.ts` — maps spoken text to engine enum options
5. **Telnyx STT provider** — `TelnyxSTTProvider` implementation (needs API key in Supabase secrets)
6. **Telnyx full WebRTC provider** — `TelnyxWebRTCProvider` (needs SIP connection + @telnyx/webrtc SDK + API key)
7. **Provider config** — `VITE_VOICE_PROVIDER` env var on Vercel
8. **Verify** — injury firewall holds in voice mode; engine unchanged; free fallback works

---

## 7. What this explicitly does NOT do

- **Does not change the engine.** The engine stays deterministic. Voice is an input/output layer, not a decision layer.
- **Does not let the LLM decide fault.** Opus §3.1 — the LLM (if used for transcript mapping) only maps speech to enum values; it never assigns a band or decides fault.
- **Does not handle injury leads.** CD-R3 — the firewall fires identically in voice and text mode.
- **Does not replace the text chat.** Voice mode is a toggle. The customer can switch to text at any time.
- **Does not require a phone number.** This is in-browser voice (WebRTC), not a PSTN phone call. The phone hotline is Stage 3, separate.

---

*Spec prepared 2026-07-18. Provider-agnostic shell designed for migration from free (browser) to Telnyx (paid) without code changes. The free push-to-talk stays live as fallback. Companion to RECEPTIONIST-ROBOT-SPEC and CD-R3.*
