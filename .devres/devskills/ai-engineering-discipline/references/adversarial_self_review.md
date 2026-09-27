# Adversarial Self Review

## When to run

Run this review twice:

1. Before execution, to challenge the plan.
2. Before final output, to challenge the conclusions.

## Review questions

- What would be missed if the target changes fields at runtime?
- Is each conclusion proven by code, network trace, DOM runtime, logs, screenshots, or only inferred?
- Can behavior differ by logged-in/logged-out state?
- Can behavior differ by Taobao/Tmall, coupon/direct-buy, product type, time, throttling, cache, cookie, localStorage, browser, device, geo, or A/B bucket?
- Does static bundle behavior match runtime behavior?
- Are there hidden branches from risk control, fingerprinting, request signing, anti-debug, bot detection, session binding, or silent degradation?
- Does every conclusion have an evidence ID?
- Which important branches remain uncovered?

## Downgrade rule

If a claim fails review, downgrade it to `[T] pending` or `[C] conflicting evidence`. Do not keep it as `[V] verified`.
