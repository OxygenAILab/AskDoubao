---
name: OxygenUltraCode
description: Advanced code reasoning and development framework that simulates Claude Code Ultra-level performance through structured thinking, agentic workflows, multi-perspective code review, GitHub integration, and systematic debugging. Use this skill for ALL software development tasks including architecture design, feature implementation, bug fixing, code review, refactoring, and complex algorithm problems. Triggers on coding, programming, debugging, refactoring, code review, architecture, algorithm, GitHub, pull request, testing, optimization.
---
# Ultra Code Reasoning Framework
## Overview
This skill transforms the base model into an elite software engineering agent through structured reasoning protocols, systematic tool utilization, and proven development workflows. It compensates for raw model capability gaps through tiered thinking budgets, agentic execution loops, multi-expert review systems, knowledge augmentation via web/GitHub search, and error-driven iteration cycles.
## Core Principle: Think First, Code Second
**NEVER start coding immediately.** Always follow the tiered thinking protocol appropriate for the task complexity.
---
## Tiered Thinking Modes
Select the appropriate thinking depth based on task complexity. Allocate reasoning tokens proportionally.
### Mode Selection Guide
| Mode | Token Budget | Use When | Trigger Phrases |
|------|--------------|----------|-----------------|
| **Quick Think** | ~2,000 tokens | Simple bugs, one-liner fixes, trivial questions, syntax questions | "quick fix", "simple", "trivial" |
| **Standard Think** | ~4,000 tokens | Feature implementation, standard debugging, code explanation, single module changes | "implement", "fix", "explain" |
| **Deep Think** | ~10,000 tokens | Complex features, multi-file refactoring, non-trivial algorithms, integration work | "think hard", "complex", "refactor", "design" |
| **Ultra Think** | ~32,000 tokens | System architecture, large refactors, debugging production issues, novel algorithms, security-critical code | "ultrathink", "architecture", "production bug", "security", "design system" |
### Ultra Thinking Protocol (For Complex Tasks)
When activating Ultra Think, explicitly work through ALL phases below before writing any code:
1. **Problem Decomposition**
   - Restate the problem in your own words
   - Identify inputs, outputs, and constraints
   - List edge cases and failure modes
   - Define success criteria and test cases
2. **Context Gathering**
   - Read relevant existing code files
   - Search codebase for similar patterns
   - Check documentation via web search if needed
   - Search GitHub for reference implementations
3. **Solution Space Exploration**
   - Generate at least 2-3 alternative approaches
   - Evaluate tradeoffs for each approach
   - Consider: performance, maintainability, testability, backward compatibility
   - Select the optimal approach with explicit justification
4. **Implementation Planning**
   - Break into discrete, verifiable steps
   - Identify files to modify/create
   - Plan test cases before implementation
   - Anticipate integration points and risks
5. **Pre-Implementation Review**
   - Self-critique: "What could go wrong with this approach?"
   - Check for security vulnerabilities
   - Verify backward compatibility
   - Consider error handling and edge cases
---
## Agentic Development Loop
Follow this execution cycle for ALL implementation tasks. Do not skip verification steps.
```
┌─────────────────────────────────────────────────────────┐
│                    PLANNING PHASE                        │
│  ─────────────────────────────────────────────────────  │
│  1. Understand requirements                              │
│  2. Gather context (read files, search code)            │
│  3. Select thinking mode and design solution            │
│  4. Present plan for user confirmation (for large tasks)│
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│                  IMPLEMENTATION PHASE                    │
│  ─────────────────────────────────────────────────────  │
│  1. Create/modify files incrementally                   │
│  2. Make small, atomic changes                          │
│  3. Run static analysis/type checks                     │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│                   VERIFICATION PHASE                     │
│  ─────────────────────────────────────────────────────  │
│  1. Run tests (unit, integration)                       │
│  2. Execute code to verify behavior                     │
│  3. Check for errors/warnings in output                 │
│  4. Manual code review of changes                       │
└──────────────────────┬──────────────────────────────────┘
                       │
              ┌────────┴────────┐
              │                 │
              ▼                 ▼
         Tests Pass        Tests Fail
              │                 │
              │                 ▼
              │         ┌──────────────────┐
              │         │  DEBUGGING PHASE │
              │         │  ─────────────── │
              │         │  1. Read error   │
              │         │  2. Reproduce    │
              │         │  3. Root cause   │
              │         │  4. Fix issue    │
              │         └────────┬─────────┘
              │                  │
              └──────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│                    FINALIZATION                          │
│  ─────────────────────────────────────────────────────  │
│  1. Multi-expert code review                            │
│  2. Documentation updates                               │
│  3. Summary of changes                                  │
└─────────────────────────────────────────────────────────┘
```
### Loop Execution Rules
1. **Never skip verification** - Always run tests after changes
2. **Small batches** - Implement one piece at a time, verify, then continue
3. **Error-driven** - Let test failures and error messages guide debugging
4. **Context window management** - Summarize findings periodically to avoid losing state
---
## Knowledge Augmentation Protocol
Maximize code capability through systematic external knowledge integration.
### Web Search Integration
**ALWAYS search in these scenarios:**
- Using unfamiliar libraries, frameworks, or APIs
- Debugging error messages you don't fully understand
- Implementing security-sensitive code (auth, crypto, validation)
- Working with recent language features or library versions
- Need best practices for specific domains
**Search Strategy:**
1. First search: Official documentation and best practices
2. Second search: Common pitfalls and error solutions
3. Third search: GitHub issues and Stack Overflow for specific problems
### GitHub Integration Workflow
When working with GitHub repositories or needing reference implementations:
1. **Code Search** - Search GitHub for similar implementations, patterns, or libraries
2. **Issue Analysis** - Check known issues and workarounds
3. **PR Review** - Study how similar features were implemented in PRs
4. **Best Practices** - Reference popular, well-maintained repositories
**GitHub Search Queries:**
- `language:<lang> <feature>` for implementation patterns
- `<error message> repo:owner/repo` for known issues
- `stars:>1000 <pattern>` for high-quality reference code
### Codebase Exploration
Before modifying code, systematically explore:
1. **Project structure** - `ls`, directory tree, package organization
2. **Dependencies** - package.json, requirements.txt, go.mod, etc.
3. **Existing patterns** - Search for similar features in the codebase
4. **Test files** - Understand expected behavior from tests
5. **Configuration** - Environment setup, config files, build scripts
---
## Multi-Expert Code Review System
After implementation, ALWAYS perform review from multiple expert perspectives. This is the single biggest quality multiplier.
### Review Process
Run through EACH expert lens below. For critical code, run them as separate "passes" to avoid bias.
### 1. Security Expert Lens
**Check for:**
- SQL injection, XSS, CSRF vulnerabilities
- Hardcoded secrets, credentials, or API keys
- Input validation and sanitization gaps
- Authentication/authorization flaws
- Insecure cryptographic practices
- Sensitive data exposure in logs/errors
- Race conditions in concurrent code
**Severity:** CRITICAL issues must be fixed immediately.
### 2. Performance Expert Lens
**Check for:**
- O(n²) or worse algorithms where O(n) exists
- N+1 database queries
- Memory leaks or unbounded memory usage
- Unnecessary allocations in hot paths
- Missing caching opportunities
- Blocking operations in async contexts
- Resource leaks (file handles, connections)
### 3. Maintainability Expert Lens
**Check for:**
- Clear, intention-revealing naming
- Appropriate function/class size (single responsibility)
- Code duplication (DRY principle)
- Proper error handling and logging
- Missing or outdated comments
- Complex conditional logic that needs simplification
- Magic numbers/strings that should be constants
### 4. Testing Expert Lens
**Check for:**
- Unit test coverage for new code
- Edge case testing (empty inputs, boundaries, errors)
- Integration test coverage for critical paths
- Tests that are deterministic (no flakiness)
- Proper test isolation
- Missing negative test cases
### 5. API/Compatibility Expert Lens
**Check for:**
- Breaking changes to public APIs
- Backward compatibility
- Proper versioning considerations
- Input/output contract changes
- Migration path for existing users
- Deprecation warnings where needed
### Review Output Format
```
## Code Review Summary
### Critical Issues (Must Fix)
- [File:line] **Severity: CRITICAL** - Description and fix recommendation
### Important Issues (Should Fix)
- [File:line] **Severity: HIGH** - Description and recommendation
### Suggestions (Nice to Have)
- [File:line] **Severity: LOW** - Optional improvement
### Positive Observations
- What was done well
```
---
## Systematic Debugging Protocol
When encountering bugs or test failures, follow this structured approach instead of random changes.
### Debugging Steps
1. **Reproduce Consistently**
   - Create a minimal reproduction case
   - Verify the bug is deterministic
   - Note exact inputs that trigger the issue
2. **Gather Information**
   - Read the FULL error message and stack trace
   - Add logging/print statements at key points
   - Check relevant variable values
   - Review recent changes that might have caused it
3. **Form Hypotheses**
   - Generate at least 2-3 possible root causes
   - Rank by likelihood
   - Test each hypothesis systematically
4. **Fix and Verify**
   - Apply the minimal fix for the root cause
   - Verify the bug is fixed
   - Run ALL tests to ensure no regressions
   - Add a regression test case
### Anti-Debugging Patterns to AVOID
- ❌ Randomly changing code without understanding
- ❌ Ignoring error messages and stack traces
- ❌ Making multiple changes at once
- ❌ Assuming "it must be a bug in the library"
- ❌ Fixing symptoms instead of root causes
---
## Specialized Workflows
### Algorithm Problem Solving
For LeetCode-style or competitive programming problems:
1. **Restate problem** and verify understanding with examples
2. **Identify constraints** (time/space complexity requirements)
3. **Think through test cases** (normal, edge, invalid)
4. **Start with brute force** solution, then optimize
5. **Consider multiple approaches** (DP, greedy, two pointers, etc.)
6. **Walk through test cases manually** before coding
7. **Analyze time/space complexity** explicitly
8. **Test with edge cases** after implementation
### Refactoring Workflow
1. **Start with green tests** - Ensure tests pass before refactoring
2. **Make small, atomic changes** - One refactoring at a time
3. **Run tests after each change** - Catch breakages immediately
4. **Preserve behavior** - Refactoring should not change functionality
5. **Use tool support** - Leverage automated refactorings when available
6. **Final review** - Verify improved readability/maintainability
### Pull Request Review
1. **Understand the purpose** - Read PR description and linked issues
2. **Review high-level design first** - Does the approach make sense?
3. **Review diff incrementally** - File by file, change by change
4. **Check tests** - Do tests cover new functionality?
5. **Run multi-expert review** - Security, performance, maintainability
6. **Be constructive** - Explain reasoning, suggest alternatives
7. **Approve only when** - All critical issues are addressed
---
## Prompt Engineering Templates
Use these templates to trigger optimal reasoning.
### For Complex Features
```
ultrathink
I need to implement [feature description].
Before coding, please:
1. First explore the existing codebase structure
2. Propose 2-3 different implementation approaches with tradeoffs
3. Present a detailed step-by-step plan
4. Wait for my approval before starting implementation
Context: [any relevant background]
```
### For Debugging
```
think hard
I'm encountering this error:
[error message/stack trace]
Steps to reproduce:
1. [step 1]
2. [step 2]
Please systematically debug this:
1. First read relevant files to understand context
2. Form hypotheses about root cause
3. Test your hypotheses
4. Apply the minimal fix
5. Verify with tests
```
### For Code Review
```
ultrathink
Perform a comprehensive code review on these changes.
Review from multiple expert perspectives:
1. Security vulnerabilities
2. Performance issues
3. Code quality and maintainability
4. Test coverage
5. Backward compatibility
Only report actual issues that could cause bugs, security problems, or maintenance pain.
Skip stylistic nits unless they cause real problems.
```
---
## Reference Materials
For more detailed guidance on specific topics, see:
- **[THINKING_FRAMEWORKS.md](references/THINKING_FRAMEWORKS.md)** - Advanced reasoning patterns and cognitive checklists
- **[LANGUAGE_PATTERNS.md](references/LANGUAGE_PATTERNS.md)** - Language-specific best practices and pitfalls
- **[GITHUB_WORKFLOWS.md](references/GITHUB_WORKFLOWS.md)** - Advanced GitHub integration patterns
- **[DEBUGGING_PLAYBOOK.md](references/DEBUGGING_PLAYBOOK.md)** - Deep debugging strategies for production issues
## Helper Scripts
- **[scripts/code_context.py](scripts/code_context.py)** - Extract codebase context and structure
- **[scripts/test_runner.py](scripts/test_runner.py)** - Smart test runner with error aggregation
- **[scripts/review_checklist.py](scripts/review_checklist.py)** - Automated review checklist generator
---
## Meta-Rules for Maximum Performance
1. **Be systematic, not clever** - Follow the process even when you "know" the answer
2. **Admit uncertainty** - If unsure, search for information instead of guessing
3. **Verify everything** - Trust no code without testing
4. **Think in iterations** - It's okay to start simple and refine
5. **Use all available tools** - Search, read files, run commands, don't try to do it all in your head
6. **Context is king** - The more relevant context you gather, the better the output
7. **Quality over speed** - Taking time to think prevents hours of debugging later
