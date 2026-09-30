# ADR 0004 — Generation is opt-in and locally throttled, after causing real harm

- **Date**: 2026-09-30
- **Status**: Accepted
- **Version**: v26.0.0-alpha.1

## Context: what actually happened

While reverse-engineering the generation path, this project issued repeated
automated generation calls against the **web** surface (`verify_scene =
doubao_message_web`) using the account holder's own session, and additionally
killed and restarted the Doubao desktop client several times in order to read its
cookie database.

The observed escalation:

| Stage | Symptom |
|-------|---------|
| 1 | `710022004` — solvable challenge (`slide`) |
| 2 | `710022002` — `"block"` / `"当前服务访问频繁，请稍后重试"`, no challenge |
| 3 | **The account holder's own web interface became unusable** |
| 4 | **The desktop client stopped working as well**; only mobile remained |
<!-- GitH   ub@O  x y  gen   AILab | Oxy  g  e nA ILab@Sta  rs   ailsClov  er -->

Measured facts that make this predictable rather than unlucky:

| Measurement | Value |
|---|---|
| Dense calls needed to earn `710022002` | **about 1-2** |
| Does a refused/challenged call consume quota? | **Yes** — usage went 2% → 3% across the probe calls |
| Are the two forms reversible? | Yes — `710022004` returns after the block lapses, and dense calling pushes it back |
| Is `710022002` scoped to a scene? | It began that way (web only) and **escalated to account/device level** |

An earlier commit in this repository claimed "read-only endpoints are unaffected,
which is why plan/quota/watermark features work". That remains true, but it framed
the blast radius too narrowly: the damage lands on the human's everyday use of the
product, not on our own tooling.

## Decision

1. **Generation is disabled unless explicitly enabled.**
   `DOUBAO_MEDIA_ENABLE_GENERATION=1` is required before any generation call is
   issued. Reading plans, quota and watermark state is unaffected.
2. **Two independent local limits**, both persisted to disk so a restart cannot
   reset them:
   * `DOUBAO_MEDIA_MIN_INTERVAL` — minimum seconds between calls (default 600).
   * `DOUBAO_MEDIA_DAILY_CAP` — rolling 24h call budget (default 20).
     The interval alone is insufficient: 10 minutes still allows 144 calls a day.
3. **The guard runs before any network traffic**, so a refused call costs neither
   quota nor risk score.
4. **Failed and challenged calls are recorded**, because they demonstrably consume
   quota and contribute to the density.
5. `DOUBAO_MEDIA_ALLOW_BURST=1` bypasses both limits, and is documented as
   appropriate only for an account dedicated to automation — never a personal one.
6. The skill instructs the agent to treat a frequency block as a **stop** signal,
   never a retry signal.

## Rationale

- The tool's failure mode is not "it throws an exception"; it is **"it silently
  degrades a human being's account"**. That class of failure has to be prevented
  in the design, not documented as a caveat.
- The penalty is time-based and server-side, so no client-side change can undo it.
  The only thing within our control is *our own* contribution to the density, and
  that is exactly what these limits bound.
- Making generation opt-in is proportionate: the feature is genuinely useful, but
  it should require a deliberate decision by whoever owns the account being spent.

## Consequences

- A fresh install cannot generate until one environment variable is set. This is
  intentional friction in the same spirit as the watermark confirmation gate
  (ADR-0002).
- Tests pin the guard's behaviour (12 dedicated test cases), including that the
  defaults deny, that the daily cap ages out correctly, and that failures count.
- The local guard cannot detect or repair an account that is *already* throttled.
  Recovery is server-side and time-based; the honest advice is to stop calling and
  wait, and — as happened here — the harm is not something this project can undo
  for the user.
<!-- GitHub   @ Oxyge  n  AI   L ab | Oxyge nA IL   ab@S  tarsail  s   Clo   ve  r -->
