# Advanced Thinking Frameworks
## Cognitive Checklists for Elite Code Reasoning
This document contains advanced reasoning patterns used by world-class software engineers. Apply these checklists during the thinking phase to avoid common blind spots and produce higher-quality code.
---
## Table of Contents
1. [First Principles Thinking](#first-principles-thinking)
2. [Rubber Duck Debugging Protocol](#rubber-duck-debugging-protocol)
3. [Pre-Mortem Analysis](#pre-mortem-analysis)
4. [Cost-Benefit Analysis for Technical Decisions](#cost-benefit-analysis)
5. [Edge Case Generation Checklist](#edge-case-generation)
6. [API Design Review Checklist](#api-design-review)
7. [Concurrency Hazard Checklist](#concurrency-hazard-checklist)
8. [Error Handling Taxonomy](#error-handling-taxonomy)
---
## First Principles Thinking
When faced with novel problems or when existing patterns don't fit, break down to fundamentals:
### Protocol
1. **Identify existing assumptions** - "What am I taking for granted here?"
2. **Break problem into fundamental truths** - "What MUST be true regardless of implementation?"
3. **Reason up from first principles** - Build solution from truths, not analogies
4. **Test each assumption** - "What would disprove this assumption?"
### Application Example
Instead of: "Let's use Redis for caching because everyone does it."
Ask:
- What is the fundamental problem? (Reducing database load for frequent reads)
- What are the constraints? (Latency requirements, consistency needs, data size)
- What are all possible solutions? (In-memory cache, CDN, database optimization, read replicas)
- Which solution best fits the constraints?
---
## Rubber Duck Debugging Protocol
Forcing yourself to explain something step-by-step reveals logical gaps.
### Protocol
1. **State the problem clearly** - What exactly is happening vs. what should happen?
2. **Explain each step out loud (or in text)** as if explaining to a beginner
3. **When you reach a contradiction** - "Wait, that can't be right..." - you've found the bug
4. **Trace data flow** from input to output, variable by variable
5. **Question every assumption** at each step: "Why do I believe this is true?"
### Explanation Template
```
Okay, let me trace through this:
1. The function receives X as input. At this point X should be...
2. Then we do Y to X. After Y, X becomes... Wait, that's not what I expected!
3. Because if Y does Z, then X should be A, but it's actually B.
4. Oh! Because I forgot that Y also does W when condition C is true.
5. That's the bug.
```
---
## Pre-Mortem Analysis
Before implementing, imagine the code has shipped and failed catastrophically. Work backwards to find why.
### Protocol
1. **Assume failure**: "It's 6 months from now. This code caused a major production outage. Why?"
2. **Generate failure scenarios** - Brainstorm everything that could go wrong
3. **For each scenario**:
   - How likely is this?
   - What would be the impact?
   - How can we prevent it?
   - How would we detect it?
4. **Mitigate the highest risks** before they become outages
### Common Failure Scenarios to Consider
- Sudden 10x traffic spike
- Third-party service goes down
- Database connection pool exhaustion
- Memory leak over time
- Race condition under concurrency
- Invalid input from unexpected source
- Backward compatibility break
- Security vulnerability discovered
- Data corruption from partial failure
---
## Cost-Benefit Analysis for Technical Decisions
Every technical choice has tradeoffs. Make them explicit.
### Analysis Framework
For any significant decision, evaluate along these axes:
| Factor | Short Term | Long Term |
|--------|------------|-----------|
| **Development Time** | How long to build now? | How much maintenance time? |
| **Complexity** | How complex is the implementation? | How complex to debug/extend later? |
| **Performance** | What's the immediate performance? | How does it scale? |
| **Risk** | What could go wrong immediately? | What technical debt are we taking on? |
| **Flexibility** | Does it solve today's problem? | How well does it adapt to future needs? |
### Decision Heuristics
- **YAGNI (You Ain't Gonna Need It)** - Don't build for hypothetical future needs
- **KISS (Keep It Simple, Stupid)** - Prefer simple solutions when possible
- **Worse is Better** - Simple, complete solutions beat perfect, complex ones
- **Rule of Three** - Wait until you have 3 use cases before building an abstraction
---
## Edge Case Generation Checklist
Systematically enumerate edge cases before considering implementation complete.
### Input Edge Cases
- Empty inputs (empty string, empty array, null, None)
- Very large inputs (maximum size, overflow potential)
- Very small inputs (minimum values, zero, negative numbers)
- Boundary values (off-by-one errors)
- Invalid/malformed inputs (wrong type, malformed JSON, special characters)
- Duplicate values
- Already sorted/reverse sorted inputs
- Unicode/special characters
- Whitespace-only inputs
### State Edge Cases
- Uninitialized state
- Already disposed/closed resources
- Concurrent modification during iteration
- Partial failure (some operations succeeded, some failed)
- Timeout scenarios
- Retry after failure
- Idempotency (same operation called multiple times)
### Environmental Edge Cases
- Network latency/disconnection
- Disk full
- Out of memory
- Permission denied
- Clock skew between systems
- Time zone/DST transitions
- Leap years/leap seconds
---
## API Design Review Checklist
Design APIs that are intuitive, safe, and future-proof.
### Naming and Consistency
- [ ] Names clearly describe what the function does
- [ ] Consistent naming conventions throughout API
- [ ] Boolean parameters are readable at call site
- [ ] No abbreviations unless universally understood
- [ ] Function names follow verb-noun pattern
### Safety and Correctness
- [ ] Makes right thing easy, wrong thing hard
- [ ] No surprising side effects
- [ ] Resources are properly cleaned up
- [ ] Immutable by default where appropriate
- [ ] Thread-safe if intended for concurrent use
- [ ] Validates all inputs
- [ ] Fails fast on invalid usage
### Evolvability
- [ ] Can add features without breaking existing callers
- [ ] Default values are sensible
- [ ] Information hiding - don't expose internals
- [ ] Minimal surface area - don't expose more than needed
- [ ] Extension points are intentional, not accidental
### Documentation
- [ ] Document what it does, not how it does it
- [ ] Document all parameters and return values
- [ ] Document error conditions
- [ ] Provide usage examples
- [ ] Document thread safety guarantees
---
## Concurrency Hazard Checklist
Concurrency bugs are the hardest to debug. Systematically check for these.
### Race Conditions
- [ ] Check-then-act sequences (if not exists then create)
- [ ] Read-modify-write operations (increment counters)
- [ ] Lazy initialization without synchronization
- [ ] Iteration while collection may be modified
- [ ] Time-of-check to time-of-use (TOCTOU) bugs
### Deadlock/Livelock
- [ ] Locks acquired in consistent order
- [ ] No lock held while waiting for external resources
- [ ] Timeouts on all blocking operations
- [ ] No circular wait conditions
### Visibility and Atomicity
- [ ] Shared mutable state properly synchronized
- [ ] Non-atomic 64-bit writes on 32-bit systems
- [ ] Proper happens-before relationships established
- [ ] Volatile/atomic variables used correctly
- [ ] Publication of objects is safe (no partially constructed objects visible)
### Resource Issues
- [ ] Locks always released (even on exceptions)
- [ ] Thread pools properly sized and shut down
- [ ] No thread leaks
- [ ] Blocking operations not executed on event loops
---
## Error Handling Taxonomy
Classify errors to handle them appropriately, not just catch everything.
### Error Categories and Handling Strategy
| Error Type | Examples | Handling Strategy |
|------------|----------|-------------------|
| **Programmer Errors** | Null pointer, assertion failure, invalid argument | Fail fast, throw exception, fix the bug |
| **Expected Operational Errors** | File not found, network timeout, user input validation | Return error, retry if appropriate, inform user |
| **Recoverable Errors** | Rate limited, temporary unavailable, deadlock detected | Retry with backoff, circuit breaker |
| **Catastrophic Errors** | Out of memory, disk corruption, unrecoverable state | Crash gracefully, log everything, alert |
### Error Handling Anti-Patterns
- ❌ Catching Exception/Throwable and swallowing
- ❌ Returning null instead of proper error
- ❌ Using exceptions for control flow
- ❌ Logging and rethrowing (double logging)
- ❌ Generic error messages without context
- ❌ Ignoring InterruptedException
- ❌ Not cleaning up resources on error
### Good Error Messages
- What went wrong (specific, not generic)
- Where it went wrong (file, function, line)
- Context (what was being done, relevant values)
- How to fix it (if actionable)
- Include error ID for correlation
---
## Cognitive Bias Mitigation
Be aware of these common thinking traps:
1. **Confirmation Bias** - Looking for evidence that supports your theory instead of trying to disprove it
   - *Mitigation*: Actively look for evidence that you're wrong
2. **Anchoring** - Fixating on the first theory and not considering alternatives
   - *Mitigation*: Generate at least 3 possible explanations before investigating
3. **Availability Heuristic** - Judging likelihood based on how easily examples come to mind
   - *Mitigation*: Use checklists, not memory
4. **Overconfidence** - Thinking your code is correct without verification
   - *Mitigation*: Assume there are bugs; prove correctness through testing
5. **Sunk Cost Fallacy** - Continuing with a bad approach because you've already invested time
   - *Mitigation*: Be willing to throw away code and start over
6. **Premature Optimization** - Optimizing before measuring
   - *Mitigation*: Profile first, then optimize hot paths
7. **Not Invented Here** - Reusing external solutions is bad
   - *Mitigation*: Prefer battle-tested libraries over custom implementations
