# Output Gate

## Evidence-first rule

Use `No Evidence, No Conclusion` for all non-trivial claims.

Every conclusion must include one or more evidence IDs. Evidence may come from source code, runtime observation, network trace, logs, screenshots, tests, lints, command output, or documented user input.

## Conclusion grades

| Grade | Meaning | Requirement |
|---|---|---|
| `[V] verified` | Directly verified fact | Evidence ID and reproducible source |
| `[H] high-confidence inference` | Strong inference | Evidence ID plus reasoning and limits |
| `[T] pending` | Not yet proven | Required verification step |
| `[C] conflicting evidence` | Evidence disagrees | Both sides and next resolution step |

## No instant guess echo

When an answer is requested quickly, resist filling gaps with guesses. State known facts first, then pending hypotheses.

## Correction discipline

When a previous conclusion is disproven:

1. Record the original claim.
2. Record the contradicting evidence.
3. Mark the old claim superseded.
4. Add the corrected claim with evidence.
5. Mention downstream docs or decisions that may be affected.
