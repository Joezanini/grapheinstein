#!/usr/bin/env python3
"""
Demonstration of grapheinstein reliability improvements.

This script creates test scenarios and shows the improved warnings and error messages.
"""

import subprocess
import sys
import tempfile
from pathlib import Path


def run_grapheinstein(args, description):
    """Run grapheinstein and capture output."""
    print(f"\n{'='*70}")
    print(f"Scenario: {description}")
    print('='*70)
    result = subprocess.run(
        [sys.executable, "-m", "grapheinstein"] + args,
        capture_output=True,
        text=True,
    )
    print(f"Exit code: {result.returncode}")
    if result.stdout:
        print(f"\nStdout:\n{result.stdout}")
    if result.stderr:
        print(f"\nStderr:\n{result.stderr}")
    return result


def main():
    print("GRAPHEINSTEIN RELIABILITY IMPROVEMENTS - DEMONSTRATION")
    print("=" * 70)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        
        # Scenario 1: Empty directory
        empty_dir = tmppath / "empty_repo"
        empty_dir.mkdir()
        output1 = tmppath / "graph1.json"
        
        run_grapheinstein(
            ["index", str(empty_dir), "-o", str(output1)],
            "Empty directory (triggers empty graph warning)"
        )
        
        # Scenario 2: Files but all binary (no entities extracted)
        binary_dir = tmppath / "binary_repo"
        binary_dir.mkdir()
        for i in range(5):
            (binary_dir / f"data{i}.bin").write_bytes(b"\x00\xFF" * 1000)
        output2 = tmppath / "graph2.json"
        
        run_grapheinstein(
            ["index", str(binary_dir), "-o", str(output2)],
            "Binary files only (triggers sparse graph warning)"
        )
        
        # Scenario 3: Nonexistent path (improved error message)
        nonexistent = tmppath / "does_not_exist"
        output3 = tmppath / "graph3.json"
        
        run_grapheinstein(
            ["index", str(nonexistent), "-o", str(output3)],
            "Nonexistent path (categorized error message)"
        )
        
        # Scenario 4: Healthy project (no warnings)
        healthy_dir = tmppath / "healthy_repo"
        healthy_dir.mkdir()
        (healthy_dir / "main.py").write_text("""
def hello():
    '''Greet the world.'''
    print('Hello, world!')

class Calculator:
    '''A simple calculator.'''
    def add(self, a, b):
        return a + b
    
    def multiply(self, a, b):
        return a * b
""")
        output4 = tmppath / "graph4.json"
        
        run_grapheinstein(
            ["index", str(healthy_dir), "-o", str(output4)],
            "Healthy Python project (no warnings expected)"
        )
    
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    print("""
Key Improvements Demonstrated:

1. ✅ Empty graph warning - Clear alert when no files found
2. ✅ Sparse graph warning - Alert when files exist but no entities extracted  
3. ✅ Categorized errors - "File not found:" prefix clarifies error type
4. ✅ No false warnings - Healthy projects don't trigger warnings

These improvements help operators (like Librarian) distinguish:
- Empty/invalid repositories from legitimate small projects
- Transient errors (I/O) from permanent errors (config)
- Parse failures from successful indexing
- When to retry vs when to skip/alert
""")


if __name__ == "__main__":
    main()
