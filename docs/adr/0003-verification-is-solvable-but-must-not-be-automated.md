# ADR 0003 — Risk control has two forms; only one is solvable

> **Update (later the same session).** The verification render is now **solved
> and visually verified**. Driving `window.verifySDK.renderCaptcha` with
> top-level integer `aid`, a `did`, a definitely-sized container and a cleared
> `__vc_is_render__` guard mounts the official “请完成下列验证后继续” slider in an
> iframe at `rmc.bytedance.com/verifycenter/captcha/v2`. The six constraints and
> their evidence are recorded in `docs/protocol.md` §5.1.1. What remains
> unverified is only the solve→retry loop (the account was throttled when the
> render became available). The decision below is unchanged and still governs:
> we render the challenge, we never solve it programmatically.

- **Date**: 2026-09-28
- **Status**: Accepted
- **Version**: v26.0.0-alpha.1

## Context

Generation was blocked throughout development with `710022004`. Investigation
established the precise position, and then the situation changed.

**`710022004` is a challenge, not a ban.** Its payload carries a full
verification instruction:
<!-- GitHub  @Oxyge   nAI Lab | O   xy g e n A ILa  b   @Sta  r sailsClover -->

```json
{"code": 710022004, "message": "rate limited",
 "error_detail": {"ext": {"decision": "{\"code\":\"10000\",
   \"from\":\"shark_admin\",\"region\":\"cn\",\"type\":\"verify\",
   \"subtype\":\"slide\",\"detail\":\"<opaque blob>\",
   \"verify_scene\":\"doubao_message_web\",\"log_id\":\"...\"}"}}}
```

The loaded Doubao page exposes the first-party integration point for it:

```
window.verifyCenter  ->  init · initVerifyCenter · initVerifyOptions
                         autoRender · renderCaptcha · renderSecondVerifyWeb
                         closeCaptcha · getCaptchaWebId · SMS
```

matching the call site in the bundled `106.js`:

```js
verifyCenter.renderCaptcha({
  verify_data,                                  // the parsed decision object
  captchaOptions: {successCb, closeCb, errorCb},
  secondVerifyWebOptions: {scene: "4", callBack, closeCallBack},
})
```

**Two things were ruled out with evidence**, so they must not be revisited as
the cause:

| Hypothesis | Verdict | Evidence |
|---|---|---|
| Egress IP is foreign and distrusted | **False for Doubao** | Clash splits by rule: domestic hosts direct, foreign hosts via Tokyo. Measured with a domestic echo (`myip.ipip.net`) the Doubao path is 广州电信, and Doubao resolves to domestic CDN IPs (`113.96.x`, `183.60.x`). |
| The request lacks a signature | **False** | `bdms.frontierSign(query)` returns a valid `X-Bogus`, and attaching it explicitly changes nothing. Read-only endpoints on the same session return `code: 0`. |

**Then the error code changed** to `710022002`:

```json
{"code": 710022002, "message": "block",
 "error_detail": {"message": "当前服务访问频繁，请稍后重试"}}
```

No `decision`, no challenge. That transition happened *because of our own
probing*, which is the most important operational fact in this ADR.

## Decision

1. Model the two forms as **separate exception types** and separate guidance:
   `DoubaoRiskControl` (verifiable, has a challenge) and `DoubaoRateLimited`
   (frequency block, nothing to solve).
2. Ship `doubao_verify_challenge`, which drives the page's **own**
   `verifyCenter` in a visible window and lets the account holder solve it.
3. **Never automate the challenge itself.** No slider-solving, no blob
   re-signing, no bypass.
4. Make "do not retry" an explicit, machine-readable instruction
   (`riskControl.recoverable = false` / `nextStep`), not just prose in a skill.
5. Record the self-inflicted-block lesson in the skill so an agent does not
   repeat it: one generation per user request; never batch, never loop.

## Rationale
<!-- Gi t  H ub@ Ox  yg   en  AILab | O x yg  e  nAILa   b@S tarsailsC l over -->

- Driving `verifyCenter` uses the exact code path the product itself uses, so
  cookies, `aid`, `did`, `pageId` and the device fingerprint stay aligned with
  the blocked request. Reconstructing the CDN class
  (`bdCaptcha.CaptchaVerify`) was attempted first and produced
  `JSON.parse` errors on the opaque blob - a sign the wrapper, not the class, is
  the intended entry point.
- Solving a security challenge is the account holder's act. Automating it would
  make this tool strictly more permissive than the product, and would defeat a
  control ByteDance deliberately put in front of the user.
- The frequency block cannot be solved *at all*. Distinguishing it from the
  challenge is therefore not cosmetic: it is the difference between "one
  verification and you can continue" and "stop now or make it worse".

## Measured throttling sensitivity

Live measurements (2026-09-30) tighten the operational rule considerably:

| Observation | Value |
|---|---|
| Calls needed to trigger `710022002` from a clean state | **about 1-2** in a short window |
| Does a challenged/refused call consume quota? | **Yes** - usage went 2% -> 3% across the probe calls |
| Can the two forms alternate? | Yes - `710022004` returns once the block expires, and dense calling pushes it back to `710022002` |

Consequences: one generation per user request, real spacing between requests, and
after a successful verification exactly **one** retry - not a loop, or the account
goes straight back to the unsolvable form. `_scratch/e2e_flow.py` encodes this and
correctly refused to retry when it hit the block (exit code 3).


## Consequences

- A user-facing browser window is required to clear a challenge. Headless
  completion is intentionally unsupported.
- `scripts/live_probe.py` and the generation tools must not be used for
  exploratory probing; that is what triggered `710022002`. Verification of new
  protocol details should prefer the bundled assets (`_scratch/extract_api.py`,
  `_scratch/g2.py`) over live generation calls.
- The verification flow is implemented but **was not exercised end-to-end**,
  because doing so would have required generating while the account was already
  throttled. It is marked accordingly in `docs/protocol.md` §5.
