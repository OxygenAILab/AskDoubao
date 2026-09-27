# Bugfix Snapshot Gate

## Bugfix record

For every fixed bug or problem, create or update a `BF-*` record containing:

- Problem statement.
- Root cause.
- Changed files.
- Minimal patch summary.
- Validation performed.
- Remaining risk.
- Review state.
- Git snapshot state.
- Rollback instruction.

## Git snapshot rule

Do not create commits, tags, or snapshots unless the user explicitly asks for that action.

When a snapshot is requested:

1. Check working tree state.
2. Identify unrelated dirty files.
3. Ask or isolate if unrelated changes exist.
4. Record commit/tag/hash after the command succeeds.

## Review rule

Do not claim multi-engineer approval unless real reviewer records are provided.
