# Production Debugging Playbook
Systematic approach to debugging even the hardest production issues. Based on real-world incident response patterns from top engineering teams.
---
## Table of Contents
1. [Debugging Mindset](#debugging-mindset)
2. [The Scientific Method for Debugging](#the-scientific-method)
3. [Production Incident Response](#production-incident-response)
4. [Common Bug Categories and Patterns](#common-bug-categories)
5. [Logging and Observability](#logging-and-observability)
6. [Heisenbugs and Flaky Tests](#heisenbugs-and-flaky-tests)
7. [Performance Issues](#performance-issues)
8. [Post-Mortem Template](#post-mortem-template)
---
## Debugging Mindset
The hardest part of debugging is your own psychology.
### Core Principles
1. **It's never "impossible"** - The computer is never wrong. If it's happening, there's a reason.
2. **Question everything** - Especially your assumptions. "That can't be the cause" is how you waste hours.
3. **Divide and conquer** - Binary search the problem space. Eliminate possibilities systematically.
4. **Change one thing at a time** - If you change two things and it works, you don't know which fixed it.
5. **Reproduce first, fix second** - If you can't reproduce it, you can't prove you fixed it.
6. **Read the error message** - It's telling you exactly what's wrong. Read the WHOLE message.
### Cognitive Traps to Avoid
- **"That worked yesterday"** - So what changed? Everything is a suspect.
- **"It must be the framework/library"** - 99% of the time it's your code.
- **"I'll just try this random thing"** - This is how you make things worse.
- **"This is too simple to be the bug"** - Bugs love simple things.
- **Confirmation bias** - Don't look for evidence you're right; look for proof you're wrong.
---
## The Scientific Method
Apply the scientific method to every bug:
### Step 1: Define the Problem Clearly
- What exactly is happening? (Not "it's broken" - be specific)
- What should be happening instead?
- When did it start happening?
- What is the scope? (All users? Specific users? Specific browsers?)
- What changed recently? (Deploys, config changes, traffic patterns)
**Template:** "When [action] happens, [observed behavior] occurs instead of [expected behavior]. This started at [time] after [change]."
### Step 2: Gather Evidence
- **Read logs** - All of them. Application logs, server logs, database logs, load balancer logs.
- **Check metrics** - Error rates, latency, CPU, memory, disk, network.
- **Reproduce locally** - If possible, create a minimal reproduction case.
- **Get a stack trace** - Not just the error message, the full trace.
- **Look at recent changes** - `git log`, deploy history, config diffs.
- **Talk to witnesses** - What did users see? What did other engineers notice?
### Step 3: Form Hypotheses
Generate at least 3 possible explanations. Rank them by likelihood.
**Good hypothesis:** "The null pointer exception on line 147 happens because `user.getSession()` returns null when the session expired, and we don't check for that."
**Bad hypothesis:** "There's a bug in the JVM."
### Step 4: Test Hypotheses
- Design experiments that PROVE or DISPROVE each hypothesis
- Change ONE thing and observe the result
- If you can't test directly, add logging to gather more data
- Disprove hypotheses first - it's faster than proving them
### Step 5: Fix and Verify
- Apply the MINIMAL fix for the ROOT CAUSE
- Don't fix symptoms
- Write a regression test
- Verify the fix works in production
- Check for similar issues elsewhere in the codebase
---
## Production Incident Response
For production outages, follow this priority order:
### Severity Classification
| Severity | Definition | Response Time |
|----------|------------|---------------|
| SEV1 | Complete outage, data loss, security breach | Immediate, all hands |
| SEV2 | Major feature broken, significant user impact | < 15 minutes |
| SEV3 | Minor issue, workaround exists | < 1 hour |
| SEV4 | Cosmetic, low impact | Next business day |
### Response Playbook
1. **Stabilize first** - Mitigate impact before root causing
   - Roll back bad deploy
   - Enable feature flags
   - Scale up resources
   - Circuit break problematic endpoints
2. **Communicate** - Keep stakeholders informed
   - Status page updates
   - Internal channel updates every 15 minutes
   - Don't speculate - state facts
3. **Root cause** - Use scientific method
4. **Fix properly** - Don't leave mitigations in place permanently
5. **Post-mortem** - Document and prevent recurrence
### Stabilization Options (Before You Know Root Cause)
- **Roll back** - The #1 safest option. 90% of outages are fixed by rollback.
- **Scale up** - Add more instances, increase resources
- **Rate limit** - Shed load to prevent cascading failure
- **Disable features** - Turn off non-critical functionality
- **Fail open/closed** - Choose appropriate failure mode
- **Restart services** - For memory leaks, deadlocks, stuck states
---
## Common Bug Categories
Learn to recognize these patterns - they account for 80% of bugs.
### Off-By-One Errors
**Symptoms:** Missing last element, processing one extra element, index out of bounds at end.
**Where to look:** Loops (`<` vs `<=`), array slicing, pagination, string operations.
**Check:** Test with 0 elements, 1 element, 2 elements, N elements.
### Null/Undefined Errors
**Symptoms:** "Cannot read property X of null/undefined", NullPointerException, segmentation faults.
**Where to look:** Optional fields, API responses, database results that can be empty, cache misses.
**Check:** What happens if every single reference is null?
### Race Conditions
**Symptoms:** Works locally, fails intermittently in production. Works when you add logging. Fails under load.
**Where to look:** Shared mutable state, concurrent operations, async code without awaiting, check-then-act patterns.
**Check:** What happens if operations execute in a different order? What if two requests hit at the exact same time?
### Time Zone/Date Issues
**Symptoms:** Works during the day, fails at midnight. Dates off by one day. Wrong time for international users.
**Where to look:** Date parsing/formatting, DST transitions, leap years, server vs client time zones.
**Check:** Test with UTC, test with different time zones, test around midnight, test DST change dates.
### Caching Bugs
**Symptoms:** Old data showing up, stale reads, "but I updated it!"
**Where to look:** Cache invalidation, TTLs, CDN caches, browser caches, ORM caches.
**Check:** Is the cache actually being cleared? Are reads going to cache or database?
### Connection/Resource Leaks
**Symptoms:** Works after restart, gradually gets slower over time, "too many open files", connection timeouts.
**Where to look:** Files, database connections, network sockets, threads, memory.
**Check:** Are resources always closed? Even on error? Even on exception?
### Silent Failures
**Symptoms:** Nothing in logs, but things aren't working. Empty catch blocks. "But there was no error!"
**Where to look:** Empty catch blocks, swallowed exceptions, `if (err) return` without logging, fire-and-forget async calls.
**Check:** What happens when an error occurs? Is it logged?
---
## Logging and Observability
Good logging is the difference between debugging in 5 minutes vs 5 hours.
### What to Log
- **ERROR** - Things that break user functionality
- **WARN** - Potential problems, degraded functionality
- **INFO** - Important lifecycle events (startup, request received/sent)
- **DEBUG** - Detailed information for debugging
### Good Log Messages Include
- **Context** - What was happening? What user/request/entity?
- **Identifiers** - Request ID, user ID, trace ID for correlation
- **Relevant state** - Key variable values (not everything!)
- **Actionable information** - What went wrong and how to fix it
**Good:** `ERROR: Failed to process payment for order 12345 (user 678): card declined (code: insufficient_funds)`
**Bad:** `ERROR: Payment failed`
### Logging Anti-Patterns
- ❌ Logging secrets, passwords, PII
- ❌ Logging at the wrong level (everything is ERROR)
- ❌ Logging and rethrowing (causes double logging)
- ❌ Generic messages without context
- ❌ Logging in tight loops (performance impact)
---
## Heisenbugs and Flaky Tests
Bugs that disappear when you try to observe them are the worst.
### Common Causes
1. **Timing issues** - Race conditions that depend on execution speed
2. **Order dependence** - Tests depend on execution order or shared state
3. **Uninitialized memory** - Reading garbage values
4. **Caching** - State persists between test runs
5. **Time dependence** - Tests that depend on current date/time
6. **Network/External service flakiness** - Real network calls in tests
7. **Randomness** - Tests using random data without fixed seeds
### Debugging Strategy
1. **Run the test 100 times** - Prove it's flaky and find failure rate
2. **Add logging** - Lots of it. Log everything.
3. **Stress test** - Run in parallel, run under load, run on slow machines
4. **Isolate** - Run only that test. Does it still fail?
5. **Reverse changes** - Binary search git history to find when it started
6. **Check shared state** - Static variables, global caches, database state
---
## Performance Issues
### Systematic Performance Debugging
1. **Measure first** - Don't guess. Profile. Use real production data.
2. **Establish baseline** - What's "normal"? What's the latency/throughput SLA?
3. **Find the bottleneck** - 90% of time is spent in 10% of code. Find that 10%.
4. **Fix one thing at a time** - Measure after each change.
5. **Beware micro-optimizations** - Fix algorithmic complexity first.
### Common Performance Problems
- **N+1 queries** - One query per item in a loop
- **Missing indexes** - Full table scans on large tables
- **Synchronous I/O in hot paths** - Blocking on disk/network
- **Memory leaks** - Growing memory usage over time
- **Unbounded concurrency** - Too many goroutines/threads/connections
- **Large object allocation** - GC pressure from too many allocations
- **Chatty APIs** - Too many small network calls
### Profiling Tools by Language
- **Python:** cProfile, py-spy, memory_profiler
- **JavaScript/TypeScript:** Chrome DevTools, clinic.js, 0x
- **Go:** pprof, trace
- **Rust:** perf, valgrind, flamegraph
- **Java:** JProfiler, VisualVM, async-profiler
- **SQL:** EXPLAIN ANALYZE, slow query logs
---
## Post-Mortem Template
After every significant outage, document it. The goal is learning, not blame.
```
# Post-Mortem: [Incident Title]
**Date:** [Date and time]
**Duration:** [Start time to end time]
**Severity:** [SEV1/SEV2/SEV3]
**Impact:** [Who was affected, what was the user impact]
## Timeline
- [Time] - [Event, e.g., "Deploy v2.4.1 to production"]
- [Time] - [Event, e.g., "Alert: 500 error rate spike to 40%"]
- [Time] - [Event, e.g., "Decision to roll back"]
- [Time] - [Event, e.g., "Roll back complete, service recovered"]
## Root Cause
[Clear, specific explanation of what actually caused the issue. Not "human error" - go deeper.]
## Contributing Factors
- What factors made this possible?
- What gaps in our process/tooling/tests allowed this?
- Why didn't our monitoring/alerting catch this earlier?
## What Went Well
- [e.g., "Rollback procedure worked as expected"]
- [e.g., "Team communicated effectively"]
## What Went Wrong
- [e.g., "We didn't test with large payloads"]
- [e.g., "Alert fired 20 minutes after impact started"]
## Action Items
- [ ] [Action 1 - specific, with owner and deadline]
- [ ] [Action 2 - specific, with owner and deadline]
- [ ] [Action 3 - specific, with owner and deadline]
## Lessons Learned
[Key takeaways that will prevent this class of issue in the future]
```
---
## Debugging Wisdom
- "Debugging is twice as hard as writing the code in the first place. Therefore, if you write the code as cleverly as possible, you are, by definition, not smart enough to debug it." - Brian Kernighan
- The bug is in the place you haven't looked yet.
- If you've been stuck for an hour, step away. Take a walk. Explain the problem to someone else.
- When you find the bug, you'll realize it was obvious all along.
- The most dangerous phrase is "That's impossible."
- It always works on your machine. Production is a different place.
