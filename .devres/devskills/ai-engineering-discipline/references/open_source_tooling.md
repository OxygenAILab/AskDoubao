# Open Source Tooling Gate

## Tool scouting rule

Before writing custom tooling or doing large manual analysis, scout mature open-source tools, especially GitHub projects, that can improve coverage, reliability, or speed.

Useful categories include:

- Repository search and indexing.
- JavaScript AST parsing and traversal.
- Bundle analysis and dependency graphing.
- Source map handling.
- Deobfuscation and beautification.
- Browser automation and screenshots.
- HAR, PCAP, and network trace analysis.
- JSON, Markdown, JavaScript, and TypeScript validation.
- Static analysis and linting.

## Adoption gate

Evaluate each candidate before use:

| Factor | Required question |
|---|---|
| Fit | Does it solve this exact task? |
| Maintenance | Is it active enough for the use case? |
| License | Is the license acceptable? |
| Platform | Does it work on the current OS/runtime? |
| Install friction | Can it be installed reproducibly? |
| Safety | Does it run unknown code or risky install scripts? |
| Reproducibility | Can the command and version be recorded? |
| Evidence grade | Can output be cross-checked? |

## Provenance rule

Record:

- Repo URL.
- Version, release, or commit.
- License.
- Install command, if any.
- Execution command.
- Input scope.
- Output artifact.
- Known limitations.
- Cross-check method.

## Blind-trust prohibition

Do not convert tool output directly into final conclusions. Cross-check important findings against source code, runtime behavior, network trace, logs, screenshots, tests, or manual sampling.

## Reinvention rule

Write custom scripts only when no suitable tool exists, existing tools are unsafe/unreproducible, or project constraints require custom logic.
