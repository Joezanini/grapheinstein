# Grapheinstein Failure Analysis

This document describes failure modes identified in grapheinstein when rebuilding public graphs from upstream git (used by Lursa Librarian).

## Identified Issues

### 1. Empty Graph Success (Low Severity)
**Symptom**: Indexing an empty directory or a directory where all files are skipped produces exit code 0 and creates a valid but empty graph.

**Impact**: Librarian may accept an empty graph as valid when all parse attempts failed.

**Root Cause**: No validation that the graph contains meaningful content after indexing.

**Fix**: Add optional warning or validation check for graphs with zero parsed entities.

### 2. Generic Exception Swallowing (Medium Severity)
**Location**: `cli.py:219-220`
```python
except Exception as exc:  # noqa: BLE001
    _fail(f"Indexing failed: {exc}", 1)
```

**Symptom**: Generic `except Exception` catches hide the true error type, making debugging harder.

**Impact**: Librarian sees "Indexing failed: <message>" without context about whether it's retryable (network) vs permanent (invalid project).

**Root Cause**: Over-broad exception handling at CLI boundary.

**Fix**: More specific exception handling with better error messages indicating error category.

### 3. Parse Skips Not Prominent (Low-Medium Severity)
**Symptom**: When many files fail to parse, skips are shown in the summary table but not prominently flagged.

**Impact**: Operators may not notice that most of the project failed to index.

**Root Cause**: parse_skips is just another metric in the summary.

**Fix**: Add warning threshold when skip ratio is high (e.g., >50% of files).

### 4. Timeout Configuration Unclear (Medium Severity)
**Symptom**: Setting timeout via config file requires specific YAML syntax; no runtime warning when approaching timeout.

**Impact**: Librarian may hit timeout without warning, producing partial graphs.

**Root Cause**: timeout_seconds is only checked at phase boundaries, not continuously.

**Fix**: Log warning when 80% of timeout budget consumed; document timeout behavior better.

### 5. Exit Code Ambiguity (Low Severity)
**Current exit codes**:
- 0: Success
- 1: General error (many different causes)
- 2: Large repo rejected
- 3: Timeout

**Symptom**: Exit code 1 covers FileNotFoundError, OSError, ConfigError, GraphError, MediaExtrasError, and generic exceptions.

**Impact**: Librarian can't distinguish transient errors from permanent failures.

**Fix**: Consider more specific exit codes or at least log error category clearly.

### 6. Atomic Write Not Fully Robust (Low Severity)
**Location**: `graph.py:640-656` `_atomic_write_bytes()`

**Symptom**: Uses temp file + rename but doesn't explicitly fsync.

**Impact**: On system crash, partial writes could corrupt output even with atomic rename.

**Root Cause**: Python's atomic write pattern doesn't guarantee durability without fsync.

**Fix**: Add fsync before rename for critical paths (optional for performance reasons).

### 7. No Explicit Empty Graph Detection (Medium Severity)
**Symptom**: A graph with only the root directory node and no files/entities is considered valid.

**Impact**: Librarian may diff against an empty graph and think everything was deleted.

**Root Cause**: No validation of minimum useful content.

**Fix**: Add validation warning when graph has <2 nodes or zero entities.

## Test Scenarios

| Scenario | Current Behavior | Expected | Status |
|----------|-----------------|----------|--------|
| Nonexistent path | Exit 1, clear error | Exit 1 | ✓ OK |
| Empty directory | Exit 0, empty graph | Exit 0 + warning | ⚠ Needs improvement |
| All files skip | Exit 0, empty graph | Exit 0 + warning | ⚠ Needs improvement |
| Broken .gitignore | Exit 0, warning logged | Exit 0 | ✓ OK (best-effort) |
| Invalid output path | Exit 1, clear error | Exit 1 | ✓ OK |
| Disk full | Exit 1, OSError | Exit 1 | ✓ OK |
| Timeout (real) | Exit 3 | Exit 3 | ✓ OK |
| Timeout (not triggered) | Exit 0 | Exit 0 | ⚠ Test needed |

## Recommendations

### High Priority
1. ✅ Add empty/sparse graph detection with warning
2. ✅ Improve CLI exception handling specificity
3. ✅ Add warning for high skip ratios

### Medium Priority
4. ⚠ Document timeout behavior in README
5. ⚠ Add timeout warning at 80% threshold
6. ⚠ Better error messages with retry hints

### Low Priority
7. ⚠ More granular exit codes
8. ⚠ Optional fsync for durability

## Implementation Plan

1. Add `GraphEmptyWarning` or similar for sparse graphs
2. Refactor CLI exception handling to categorize errors
3. Add skip ratio warning in summary output
4. Add tests for new warning conditions
5. Update README with troubleshooting section
