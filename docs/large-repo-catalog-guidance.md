# Large-Repo Catalog Guidance

This document provides guidance for operators running grapheinstein against large catalogs of diverse repositories (e.g., Lursa Librarian library refresh).

## Background

Grapheinstein includes advisory large-repo preflight gates to prevent long-running or resource-intensive indexing operations. When indexing a catalog of ~1000+ repositories with varying characteristics (CLIs, SDKs, docs-heavy projects), some repos may trip these advisory gates.

## Exit Code 2: Advisory Preflight Rejects

Exit code 2 indicates an **advisory large-repo preflight rejection**, not a crash or hard failure. These gates are designed to be tunable for different corpus characteristics.

### Common Preflight Rejections

1. **`max_non_code_share` (default 0.85)**
   - Triggered when >85% of repository bytes are non-code files
   - Common in SDK/docs-heavy repositories
   - Failure code: `large_repo_preflight_max_non_code_share`

2. **`max_reference_scan_ops` (default 5,000,000)**
   - Triggered when `eligible_scan_files * unique_basenames > 5M`
   - Protects against O(files × basenames) reference linking cost
   - Common in large monorepos with many unique file basenames
   - Failure code: `large_repo_preflight_max_reference_scan_ops`

3. **Hard Caps (always enforced)**
   - `max_total_bytes` (default 800MB): total repository size
   - `max_file_count` (default 20,000): total file count
   - Cannot be bypassed with `--allow-large-repo`

## Structured Failure Output

When indexing fails with exit code 2, grapheinstein writes `<output>.failure.json` with structured data:

```json
{
  "success": false,
  "exit_code": 2,
  "error_message": "Large-repo preflight rejected this index: ...",
  "error_category": "large_repo",
  "timestamp": "2026-09-14T15:11:55Z",
  "details": {
    "failure_codes": ["large_repo_preflight_max_non_code_share"],
    "tripped_gates": ["max_non_code_share (0.865 > 0.85)"],
    "metrics": {
      "total_bytes": 12345678,
      "file_count": 1234,
      "estimated_scan_ops": 4500000,
      "non_code_share": 0.865
    },
    "thresholds": {
      "max_total_bytes": 838860800,
      "max_file_count": 20000,
      "max_reference_scan_ops": 5000000,
      "max_non_code_share": 0.85
    },
    "suggested_flags": ["--code-only"]
  }
}
```

This enables automation tools to:
- Distinguish preflight rejects from crashes
- Parse failure reasons without scraping stderr
- Get actionable suggestions per failure type
- Track metrics for threshold tuning

## Recommendations for Catalog Operators

### Option 1: Use `--code-only` (Recommended for Mixed Catalogs)

The `--code-only` flag:
- Applies default ignores for `docs/` and `discovery_cache/`
- Restricts reference linking sources to Tree-sitter code extensions
- Allows repos to pass `max_non_code_share` gate by excluding heavy doc dirs

```bash
grapheinstein index /path/to/repo --code-only -o graph.json
```

**When to use:**
- Mixed catalog with both code-focused and docs-heavy repos
- You want reference linking but need to exclude generated docs
- You want consistent behavior across diverse repos

### Option 2: Tune Thresholds in Config

Create a catalog-friendly config with relaxed advisory gates:

```yaml
# ~/.grapheinstein/config-catalog.yaml
max_non_code_share: 0.90  # Allow up to 90% non-code
max_reference_scan_ops: 10000000  # 10M ops (double default)
```

Then use it for catalog runs:

```bash
grapheinstein index /path/to/repo --config ~/.grapheinstein/config-catalog.yaml -o graph.json
```

**When to use:**
- You have compute resources to handle larger scan operations
- You want to index docs-heavy repos without `--code-only`
- You want to profile actual resource usage before setting limits

### Option 3: Per-Repo `--allow-large-repo`

Bypass advisory gates on a per-repo basis:

```bash
grapheinstein index /path/to/repo --allow-large-repo -o graph.json
```

**When to use:**
- You know a specific repo is safe despite tripping gates
- You're doing one-off or exploratory indexing
- You want hard caps (bytes/files) to still apply

**Not recommended for:**
- Batch/catalog operations without per-repo profiling
- Repos you haven't inspected manually

## Analyzing Failure Patterns

After a catalog run, analyze failure patterns from `.failure.json` files:

```python
import json
from pathlib import Path
from collections import Counter

failure_codes = Counter()
metrics = {"non_code_share": [], "estimated_scan_ops": []}

for failure_file in Path("catalog_output").glob("**/*.failure.json"):
    with open(failure_file) as f:
        failure = json.load(f)
    
    if failure.get("error_category") == "large_repo":
        details = failure.get("details", {})
        for code in details.get("failure_codes", []):
            failure_codes[code] += 1
        
        m = details.get("metrics", {})
        if "non_code_share" in m:
            metrics["non_code_share"].append(m["non_code_share"])
        if "estimated_scan_ops" in m:
            metrics["estimated_scan_ops"].append(m["estimated_scan_ops"])

print("Failure code distribution:")
for code, count in failure_codes.most_common():
    print(f"  {code}: {count}")

print("\nMetrics distribution:")
for metric, values in metrics.items():
    if values:
        print(f"  {metric}: median={sorted(values)[len(values)//2]:.3f}, max={max(values):.3f}")
```

Use this analysis to decide:
- Should you use `--code-only` for the entire catalog?
- Should you increase `max_non_code_share` or `max_reference_scan_ops`?
- Are there outlier repos that need per-repo handling?

## Example: Lursa Librarian Catalog Refresh (2026-09-13)

**Results:**
- Total repos: 1184
- Success: 600
- Unchanged: 180
- Failed: 404
  - grapheinstein-failed: 401
  - clone-failed: 3

**Failure Analysis (from debug log):**
- ~385 large-repo preflight rejections
  - ~360 `max_non_code_share` (0.865 > 0.85)
  - ~25 `max_reference_scan_ops` (ops > 5M)

**Recommended Action:**
1. Use `--code-only` for entire catalog (simplest, most consistent)
2. Or increase `max_non_code_share` to 0.90 in catalog config
3. Retry the 401 failed repos with updated settings
4. Parse `.failure.json` files to confirm preflight rejects vs real failures

**Expected Outcome:**
- ~360 repos pass with `--code-only` or increased `max_non_code_share`
- ~25 repos may need `max_reference_scan_ops` increase or `--allow-large-repo`
- Remaining failures (~16) are likely real issues (clone failures, corrupted repos, etc.)

## Summary

- **Exit code 2 = advisory preflight reject**, not a crash
- **Use structured `.failure.json`** for machine-readable failure analysis
- **Start with `--code-only`** for mixed catalogs
- **Tune thresholds** based on failure pattern analysis
- **Hard caps** (bytes/files) always apply for safety
