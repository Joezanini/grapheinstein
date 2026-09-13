#!/usr/bin/env python3
"""
Simulate how Librarian might invoke grapheinstein.

This helps us reproduce the "grapheinstein_ok=false with empty stderr" issue.
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path


def test_subprocess_cli(repo_path: Path):
    """Test subprocess invocation like Librarian might do."""
    print(f"\n{'='*70}")
    print(f"Testing: {repo_path}")
    print('='*70)
    
    output_file = Path(tempfile.mktemp(suffix=".json"))
    
    # Method 1: subprocess with explicit stderr capture
    result = subprocess.run(
        [sys.executable, "-m", "grapheinstein", "index", str(repo_path), "-o", str(output_file)],
        capture_output=True,
        text=True,
        timeout=120,
    )
    
    print(f"Exit code: {result.returncode}")
    print(f"Stdout length: {len(result.stdout)}")
    print(f"Stderr length: {len(result.stderr)}")
    print(f"Output file exists: {output_file.exists()}")
    
    if output_file.exists():
        try:
            with open(output_file) as f:
                graph = json.load(f)
            node_count = len(graph.get("nodes", []))
            print(f"Graph nodes: {node_count}")
            grapheinstein_ok = node_count > 1  # Simple check
        except Exception as e:
            print(f"Graph load error: {e}")
            grapheinstein_ok = False
    else:
        grapheinstein_ok = False
    
    print(f"grapheinstein_ok: {grapheinstein_ok}")
    
    if not grapheinstein_ok and not result.stderr:
        print("⚠️  REPRODUCES ISSUE: grapheinstein_ok=false with empty stderr!")
    
    if result.stderr:
        print(f"\nStderr preview:\n{result.stderr[:500]}")
    
    return {
        "grapheinstein_ok": grapheinstein_ok,
        "exit_code": result.returncode,
        "stderr": result.stderr,
        "stdout": result.stdout,
    }


def test_python_api(repo_path: Path):
    """Test Python API invocation."""
    print(f"\n{'='*70}")
    print(f"Testing Python API: {repo_path}")
    print('='*70)
    
    output_file = Path(tempfile.mktemp(suffix=".json"))
    
    try:
        from grapheinstein.api import index
        result = index(
            repo_path,
            output=output_file,
            show_progress=False,
        )
        print(f"Success: {result.output_path}")
        print(f"Nodes: {result.stats.total_nodes}")
        grapheinstein_ok = result.stats.total_nodes > 1
        return {"grapheinstein_ok": grapheinstein_ok, "exception": None}
    except Exception as e:
        print(f"Exception: {type(e).__name__}: {e}")
        return {"grapheinstein_ok": False, "exception": str(e)}


def main():
    print("LIBRARIAN INVOCATION SIMULATION")
    print("="*70)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        
        # Scenario 1: Empty repo
        empty = tmppath / "empty"
        empty.mkdir()
        test_subprocess_cli(empty)
        test_python_api(empty)
        
        # Scenario 2: Repo with files but no code
        binary = tmppath / "binary"
        binary.mkdir()
        (binary / "data.bin").write_bytes(b"\x00\xFF" * 100)
        test_subprocess_cli(binary)
        
        # Scenario 3: Tiny valid repo
        tiny = tmppath / "tiny"
        tiny.mkdir()
        (tiny / "main.py").write_text("def hello(): pass")
        test_subprocess_cli(tiny)


if __name__ == "__main__":
    main()
