# GitHub Integration Workflows
Maximize code capability through systematic use of GitHub resources.
---
## GitHub Search Strategy
### Search Syntax Mastery
| Qualifier | Example | Purpose |
|-----------|---------|---------|
| `language:` | `language:python async http` | Restrict to specific language |
| `stars:` | `stars:>1000 jwt auth` | Find popular, battle-tested code |
| `pushed:` | `pushed:>2025-01-01 react hooks` | Find actively maintained code |
| `filename:` | `filename:Dockerfile multi-stage` | Search specific filenames |
| `repo:` | `repo:tiangolo/fastapi dependency` | Search within specific repo |
### Search Query Construction
**Implementation patterns:**
```
language:<lang> stars:>500 <feature>
```
**Bug solutions:**
```
<error message> language:<lang> in:issues is:closed
```
---
## Reference Implementation Mining
When implementing a new feature, find 2-3 high-quality references:
1. Find candidates using search
2. Filter for quality (stars, activity, tests)
3. Read tests first - they show intended behavior
4. Trace the happy path
5. Study error handling
6. Note edge cases
7. Identify tradeoffs
8. Adapt, don't copy
---
## Issue and PR Analysis
### Analyzing Issues
- Search for your exact error message
- Read closed issues first
- Look for workarounds in comments
- Note version numbers
- Check linked PRs
### Analyzing PRs
- Read PR description for motivation
- Read review comments - what did reviewers catch?
- Look at diff incrementally
- Check for test changes
- Note requested changes
---
## Repository Quality Assessment
### High Quality Signals
- ✅ > 1000 stars
- ✅ Active maintenance (commits within 3 months)
- ✅ Good test coverage
- ✅ Responsive maintainers
- ✅ Clear documentation
- ✅ Used by well-known projects
### Red Flags
- ❌ Known vulnerabilities without patches
- ❌ Hardcoded secrets
- ❌ No tests
- ❌ Last commit > 1 year ago
- ❌ No license
---
## Learning from Open Source
### High-Quality Repositories to Study
- **General:** sqlite, linux, redis
- **Python:** fastapi, requests, django
- **JavaScript/TypeScript:** react, vite, next.js
- **Go:** go stdlib, kubernetes, etcd
- **Rust:** rust stdlib, tokio, ripgrep
### Active Reading Technique
1. Start with main entry point
2. Follow data flow
3. Draw architecture diagrams
4. Ask "why" not just "what"
5. Look for patterns
6. Find the tests
7. Clone and run with debugger
