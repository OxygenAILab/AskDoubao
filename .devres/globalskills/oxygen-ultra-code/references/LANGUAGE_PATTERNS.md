# Language-Specific Patterns and Pitfalls
Common mistakes, idioms, and best practices for popular programming languages. Consult this when working in a specific language to avoid footguns and write idiomatic code.
---
## Table of Contents
1. [Python](#python)
2. [JavaScript/TypeScript](#javascripttypescript)
3. [Go](#go)
4. [Rust](#rust)
5. [Java](#java)
6. [C/C++](#cc)
7. [SQL](#sql)
---
## Python
### Common Pitfalls
- **Mutable default arguments**: `def func(items=[])` - default is created once, shared across calls
  - Fix: Use `None` as default, create inside function
- **Late binding closures**: Loop variables captured by reference, not value
  - Fix: Use default argument `lambda x=x: x` or functools.partial
- **`__del__` is unreliable**: Don't use for cleanup; use context managers (`with` statement)
- **Integer caching**: `is` works for small ints (-5 to 256) but not for larger ones; always use `==`
- **Floating point precision**: Never compare floats directly with `==`; use tolerance
- **Circular imports**: Cause partially initialized modules; restructure imports
- **`import *`**: Pollutes namespace, causes name conflicts; avoid
- **GIL limitations**: CPU-bound tasks won't parallelize with threads; use multiprocessing
### Idiomatic Patterns
```python
# Context managers for resource management
with open("file.txt") as f:
    content = f.read()
# List comprehensions (avoid map/filter for simple cases)
squares = [x**2 for x in numbers if x > 0]
# EAFP (Easier to Ask Forgiveness than Permission) over LBYL
try:
    value = dct[key]
except KeyError:
    value = default
# Pathlib over os.path
from pathlib import Path
path = Path(__file__).parent / "data" / "file.txt"
# Type hints for clarity
def greet(name: str) -> str:
    return f"Hello {name}"
```
### Performance Tips
- Use built-in functions and standard library (they're implemented in C)
- Generators for large datasets instead of lists
- `join()` for string concatenation instead of `+` in loops
- Use `collections` (deque, defaultdict, Counter) for appropriate data structures
- Avoid attribute lookups in hot loops; cache in local variables
---
## JavaScript/TypeScript
### Common Pitfalls
- **`this` binding**: Depends on call site, not definition; use arrow functions or `.bind()`
- **Automatic Semicolon Insertion (ASI)**: Can cause unexpected behavior; always use semicolons
- **`==` vs `===`**: Always use `===` (strict equality) to avoid type coercion bugs
- **Hoisting**: `var` declarations are hoisted; use `let`/`const` (block-scoped)
- **Promise errors**: Unhandled promise rejections cause crashes; always `.catch()` or `await` with try/catch
- **`0.1 + 0.2 !== 0.3`**: Floating point precision; use integer math or libraries for decimals
- **`typeof null === "object"`**: Historic bug; check with `x === null`
- **Array sort**: Defaults to string comparison; always pass comparator
- **Reference equality for objects**: `{} === {}` is false; deep compare values
### Idiomatic Patterns
```typescript
// Optional chaining and nullish coalescing
const name = user?.profile?.name ?? "Anonymous";
// Destructuring
const { id, name, ...rest } = user;
const [first, second, ...remaining] = array;
// Async/await for async code
async function fetchData() {
  try {
    const response = await fetch(url);
    return await response.json();
  } catch (err) {
    console.error("Fetch failed:", err);
    throw err;
  }
}
// Array methods
const result = items
  .filter(item => item.active)
  .map(item => transform(item))
  .reduce((acc, item) => acc + item.value, 0);
// Immutability patterns
const newState = { ...oldState, updated: true };
const newArray = [...oldArray, newItem];
```
### TypeScript Specific
- Enable `strict` mode in tsconfig.json
- Prefer `unknown` over `any`; narrow with type guards
- Use discriminated unions for state machines
- Avoid `as` type assertions; validate at runtime if needed
- Use utility types: `Partial`, `Pick`, `Omit`, `ReturnType`, `Awaited`
---
## Go
### Common Pitfalls
- **Nil interfaces**: Interface with nil value != nil interface; be careful returning nil pointers
- **Loop variable capture**: Same as Python - loop variables reused in goroutines
  - Fix: `for i := range items { i := i; go func() { use(i) }() }`
- **Unbuffered channels**: Block until both sender and receiver are ready
- **`defer` in loops**: Defers run at function end, not loop end; can exhaust resources
- **Shadowed variables**: `:=` can accidentally shadow outer variables
- **Range over value**: `for _, v := range slice` gets a copy; modify via index
- **Error checking**: Don't ignore errors with `_`; handle or explicitly ignore
- **Map iteration order**: Not defined; don't rely on it
- **Data races**: Use `-race` flag; protect shared state with mutexes or channels
### Idiomatic Patterns
```go
// Error handling - check immediately
if err != nil {
    return fmt.Errorf("failed to do X: %w", err)
}
// Channels for synchronization
done := make(chan struct{})
go func() {
    // do work
    close(done)
}()
<-done
// Context for cancellation/timeouts
ctx, cancel := context.WithTimeout(ctx, 5*time.Second)
defer cancel()
// Defer for cleanup
f, err := os.Open("file.txt")
if err != nil {
    return err
}
defer f.Close()
// Struct embedding for composition
type Client struct {
    *http.Client
    baseURL string
}
```
### Proverbs
- Don't communicate by sharing memory; share memory by communicating
- Concurrency is not parallelism
- Channels orchestrate; mutexes serialize
- The bigger the interface, the weaker the abstraction
- Make the zero value useful
- A little copying is better than a little dependency
---
## Rust
### Common Pitfalls
- **Borrow checker fights**: Fighting the borrow checker usually means design issue
- **Lifetimes**: Don't over-annotate; let compiler infer when possible
- **`unwrap()`/`expect()`**: Panic on None/Err; use `?` operator or proper error handling
- **Move semantics**: Values moved; can't use after move
- **`&mut` aliasing**: Can't have multiple mutable references; compiler enforces
- **String vs &str**: Understand owned vs borrowed; `String` is owned, `&str` is borrowed
- **Interior mutability**: Use `Cell`, `RefCell`, `Mutex`, `RwLock` appropriately
- **Drop order**: Variables dropped in reverse order of declaration
- **Trait bounds**: Don't over-constrain; use only what you need
### Idiomatic Patterns
```rust
// ? operator for error propagation
fn read_file() -> Result<String, io::Error> {
    let mut f = File::open("file.txt")?;
    let mut s = String::new();
    f.read_to_string(&mut s)?;
    Ok(s)
}
// Pattern matching
match value {
    Some(x) if x > 0 => println!("Positive: {}", x),
    Some(0) => println!("Zero"),
    None => println!("None"),
    _ => println!("Negative"),
}
// Iterators instead of indexing
let sum: i32 = numbers.iter()
    .filter(|&&x| x > 0)
    .map(|&x| x * x)
    .sum();
// Newtype pattern for type safety
struct UserId(u64);
struct OrderId(u64);
// Traits for abstraction
trait Repository {
    fn get(&self, id: Id) -> Result<Entity>;
    fn save(&self, entity: Entity) -> Result<()>;
}
```
### Error Handling
- Use `thiserror` for library errors
- Use `anyhow` for application errors
- Add context with `.wrap_err()` or `.with_context()`
- Don't use `unwrap()` in production code except:
  - Prototyping
  - Tests
  - When you can prove it's safe (with comment)
---
## Java
### Common Pitfalls
- **NullPointerException**: Use `Optional`, null checks, or `@NonNull` annotations
- **Reference equality**: `==` compares references, not content; use `.equals()` for objects
- **Integer caching**: Same as Python; `==` works for -128 to 127 only
- **ConcurrentModificationException**: Don't modify collection while iterating; use Iterator.remove()
- **Memory leaks**: Static collections holding references, unclosed resources, inner classes
- **Checked exceptions**: Don't catch Exception; catch specific exceptions
- **`finalize()`**: Deprecated and unreliable; use try-with-resources
- **String concatenation in loops**: Use StringBuilder
- **Synchronization**: Always synchronize on shared mutable state; use java.util.concurrent
### Idiomatic Patterns
```java
// Try-with-resources for AutoCloseable
try (var reader = Files.newBufferedReader(path)) {
    return reader.lines().toList();
}
// Optional for nullable values
return Optional.ofNullable(user)
    .map(User::getAddress)
    .map(Address::getCity)
    .orElse("Unknown");
// Streams for collection processing
var result = items.stream()
    .filter(Item::isActive)
    .map(Item::getValue)
    .sorted()
    .toList();
// Records for immutable data (Java 16+)
public record Point(int x, int y) {}
// Builder pattern for complex objects
var user = User.builder()
    .name("Alice")
    .email("alice@example.com")
    .build();
```
---
## C/C++
### Common Pitfalls
- **Buffer overflows**: Always check bounds; use std::string/std::vector
- **Memory leaks**: Every new needs a delete; prefer smart pointers
- **Dangling pointers**: Pointer to freed memory; use RAII
- **Double free**: Don't free memory twice; set pointers to null after free
- **Use-after-free**: Don't use objects after they're destroyed
- **Undefined behavior**: Signed integer overflow, null dereference, out-of-bounds access
- **Object slicing**: Derived objects copied as base lose derived parts; use pointers/references
- **Include order**: Don't rely on transitive includes; include what you use
- **`sizeof` on arrays**: Decays to pointer size when passed to function
### Modern C++ Idioms (C++17/20)
```cpp
// Smart pointers
auto ptr = std::make_unique<MyClass>(args);  // unique ownership
auto shared = std::make_shared<MyClass>(args); // shared ownership
// RAII - destructors clean up automatically
class File {
    FILE* f;
public:
    File(const char* path) : f(fopen(path, "r")) {}
    ~File() { if (f) fclose(f); }
    // Delete copy to prevent double-free
    File(const File&) = delete;
    File& operator=(const File&) = delete;
};
// Range-based for loops
for (const auto& item : items) {
    process(item);
}
// std::optional for nullable values (C++17)
std::optional<User> find_user(int id) {
    if (exists) return user;
    return std::nullopt;
}
// std::variant for type-safe unions (C++17)
using Value = std::variant<int, double, std::string>;
```
---
## SQL
### Common Pitfalls
- **SQL injection**: Never concatenate user input; use parameterized queries
- **N+1 queries**: Avoid loops with queries; use JOINs or batch loading
- **Missing indexes on foreign keys and WHERE clauses**: Check with EXPLAIN
- **SELECT ***: Specify columns; avoid pulling unnecessary data
- **Implicit type conversion**: Can prevent index usage; match types
- **NULL comparisons**: `= NULL` doesn't work; use `IS NULL` / `IS NOT NULL`
- **NOT IN with NULLs**: Returns empty if subquery returns NULL; use NOT EXISTS
- **LIMIT without ORDER BY**: Non-deterministic results
- **Deadlocks**: Access tables in consistent order; keep transactions short
### Best Practices
```sql
-- Parameterized queries (not string concatenation)
SELECT id, name, email FROM users WHERE id = $1;
-- Use EXPLAIN ANALYZE to check query plans
EXPLAIN ANALYZE SELECT * FROM orders WHERE user_id = 123;
-- Pagination with keyset (not OFFSET for large datasets)
SELECT * FROM orders
WHERE id > $last_id
ORDER BY id
LIMIT 100;
-- Use CTEs for readability
WITH active_users AS (
    SELECT id, name FROM users WHERE status = 'active'
),
user_orders AS (
    SELECT user_id, COUNT(*) as order_count
    FROM orders
    GROUP BY user_id
)
SELECT u.name, COALESCE(o.order_count, 0) as orders
FROM active_users u
LEFT JOIN user_orders o ON u.id = o.user_id;
```
### Indexing Strategy
- Index columns used in WHERE, JOIN, ORDER BY, GROUP BY
- Composite indexes: most selective column first
- Covering indexes for frequent queries
- Don't over-index: indexes slow down writes
- Use partial indexes for subsets of data
