# OxygenUltraCode Skill - Usage Guide
## Installation
1. Copy the `OxygenUltraCode` folder to your skills directory:
   ```
   ~/.super_doubao/super-doubao-runtime/workspace/skills/
   ```
2. The skill will automatically activate for coding tasks.
## How It Works
This skill maximizes code reasoning capability through:
### 1. Tiered Thinking Modes
The framework enforces structured thinking before coding:
- **Quick Think** (~2k tokens): Simple fixes, syntax questions
- **Standard Think** (~4k tokens): Feature implementation, standard debugging
- **Deep Think** (~10k tokens): Complex features, refactoring, non-trivial algorithms
- **Ultra Think** (~32k tokens): System architecture, production bugs, security-critical code
**Trigger with:** `ultrathink`, `think hard`, `think harder`
### 2. Agentic Development Loop
Every implementation follows:
```
Plan → Implement → Verify → Debug → Review
```
The framework enforces verification after every change - no more "write and pray" coding.
### 3. Multi-Expert Code Review
After implementation, code is reviewed from 5 perspectives:
- 🔒 **Security Expert** - Injection, auth, crypto, secrets
- ⚡ **Performance Expert** - Algorithms, N+1 queries, memory leaks
- 📖 **Maintainability Expert** - Naming, structure, duplication
- 🧪 **Testing Expert** - Coverage, edge cases, determinism
- 🔌 **API Expert** - Backward compatibility, contracts
### 4. Knowledge Augmentation
The skill instructs the agent to:
- Search the web for documentation and best practices
- Search GitHub for reference implementations
- Mine high-quality open source for patterns
- Read Stack Overflow and GitHub issues for solutions
### 5. Systematic Debugging Protocol
Instead of random changes:
1. Reproduce consistently
2. Gather information (logs, stack traces)
3. Form multiple hypotheses
4. Test hypotheses systematically
5. Fix root cause, not symptoms
## Helper Scripts
### `scripts/code_context.py`
Analyzes codebase structure to quickly understand projects:
```bash
python scripts/code_context.py --path /path/to/project --depth 3
```
Outputs: languages used, lines of code, entry points, dependencies, directory tree.
### `scripts/test_runner.py`
Smart test runner that auto-detects frameworks and extracts errors:
```bash
python scripts/test_runner.py --path /path/to/project
```
Supports: pytest, jest, vitest, go test, cargo test, maven, gradle, npm test.
### `scripts/review_checklist.py`
Generates context-aware code review checklists:
```bash
python scripts/review_checklist.py --files file1.py file2.js --type feature
```
## Prompt Templates
### For Complex Features
```
ultrathink
I need to implement [feature description].
Before coding, please:
1. First explore the existing codebase structure
2. Propose 2-3 different implementation approaches with tradeoffs
3. Present a detailed step-by-step plan
4. Wait for my approval before starting implementation
```
### For Debugging
```
think hard
I'm encountering this error:
[error message/stack trace]
Steps to reproduce:
1. [step 1]
2. [step 2]
Please systematically debug this.
```
### For Code Review
```
ultrathink
Perform a comprehensive code review on these changes.
Review from multiple expert perspectives: security, performance, maintainability, tests, compatibility.
```
## Reference Documents
- **THINKING_FRAMEWORKS.md** - Advanced reasoning patterns, cognitive checklists, first principles thinking, pre-mortem analysis
- **LANGUAGE_PATTERNS.md** - Python, JS/TS, Go, Rust, Java, C/C++, SQL pitfalls and idioms
- **GITHUB_WORKFLOWS.md** - GitHub search strategies, reference mining, learning from open source
- **DEBUGGING_PLAYBOOK.md** - Production incident response, common bug patterns, heisenbugs, performance debugging
## Performance Tips
1. **Use `ultrathink` for complex tasks** - The extra thinking time prevents hours of debugging
2. **Let the agent explore first** - Don't rush to code; understanding context is 80% of the work
3. **Run tests frequently** - The agentic loop works best with fast feedback
4. **Ask for plans first** - For large features, review the plan before implementation
5. **Use the scripts** - code_context.py and test_runner.py save time on context gathering
## Expected Improvements
Even on base models, you should see:
- ✅ Fewer "stupid mistakes" and off-by-one errors
- ✅ Better security awareness (no hardcoded secrets, proper input validation)
- ✅ More systematic debugging (no more random changes)
- ✅ Better consideration of edge cases
- ✅ More idiomatic code following language best practices
- ✅ Better use of external knowledge (docs, GitHub, Stack Overflow)
- ✅ More thorough testing awareness
- ✅ Structured approach to complex problems
## Philosophy
The core insight is that **raw model capability is only part of performance**. Just like a senior engineer outperforms a junior engineer not because they are "smarter" but because they:
1. Follow systematic processes
2. Know what they don't know (and look it up)
3. Check their work
4. Think before coding
5. Learn from patterns and experience
6. Review from multiple perspectives
This skill encodes those engineering practices into a structured framework that any model can follow.
