# Exhaustive Execution Contract

## Budgeted exhaustive mode

Absolute exhaustiveness is often unbounded. Declare the scope, then make coverage measurable.

Required fields:

- Scope boundary.
- Included surfaces.
- Excluded surfaces.
- Coverage counters.
- Uncovered backlog.
- Exit criteria.

## Depth levels

| Level | Meaning |
|---|---|
| `L1` | Indexed or located |
| `L2` | Fields, strings, selectors, parameters, or constants extracted |
| `L3` | Call chain, data flow, or dependency path mapped |
| `L4` | Dynamic behavior observed or reproduced |
| `L5` | Cross-validated and challenged by negative/variant evidence |

## Completion rule

Do not write `complete` unless coverage counters and exit criteria support it. Use `covered within declared scope` when true total coverage is not possible.

## Backlog rule

Every uncovered branch must be recorded with reason, risk, and next verification step.
