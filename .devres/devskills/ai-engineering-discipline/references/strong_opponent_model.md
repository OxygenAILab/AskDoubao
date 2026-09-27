# Strong Opponent Model

## Large-team assumption

Treat mature targets as systems built by multiple specialized teams. Search, login, detail pages, SKU, order, payment handoff, MTOP, risk control, anti-bot, telemetry, performance, compatibility, and A/B experiments may have different owners and overlapping mechanisms.

## No-dead-code assumption

Do not call code dead, unused, noise, irrelevant, or decorative because it did not trigger once.

Every loaded script, field, parameter, selector, SDK hook, event listener, storage key, network request, and telemetry event is presumed intentional until negative evidence proves otherwise within a declared scope.

## Asset status labels

| Label | Meaning |
|---|---|
| `[A] active` | Observed running or clearly called |
| `[D] dormant but reachable` | Not observed running, but reachable path exists |
| `[G] gated by condition` | Controlled by login, experiment, risk, cache, product type, or similar condition |
| `[U] unknown` | Insufficient evidence |
| `[N] proven non-relevant` | Non-relevance supported by negative evidence within declared scope |

## Intent inventory fields

Record for each asset:

- Asset ID.
- Type.
- Location.
- Load condition.
- Execution condition.
- Inputs.
- Outputs.
- State touched.
- Related team/surface if inferable.
- Evidence IDs.
- Status label.
- Confidence.
- Scope limit.

## Negative evidence discipline

To mark `[N] proven non-relevant`, collect at least:

1. Search/index result.
2. Reference/call check.
3. Runtime observation or absence within a defined scenario.
4. Scope limitation explaining where the conclusion does not apply.

## Variant pressure

Challenge findings across login state, browser/device, cache, cookie, storage, experiment bucket, risk profile, product type, Taobao/Tmall, coupon/direct-buy, time, geo, and throttling.
