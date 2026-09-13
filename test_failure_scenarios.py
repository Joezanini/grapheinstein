#!/usr/bin/env python3
"""Test script to identify common failure scenarios in grapheinstein."""

import subprocess
import sys
import tempfile
from pathlib import Path


def test_nonexistent_path():
    """Test indexing a nonexistent path."""
    print("Testing nonexistent path...")
    result = subprocess.run(
        [sys.executable, "-m", "grapheinstein.cli", "index", "/nonexistent/path"],
        capture_output=True,
        text=True,
    )
    print(f"  Exit code: {result.returncode}")
    print(f"  Stderr: {result.stderr[:200]}")
    return result.returncode


def test_empty_directory():
    """Test indexing an empty directory."""
    print("\nTesting empty directory...")
    with tempfile.TemporaryDirectory() as tmpdir:
        result = subprocess.run(
            [sys.executable, "-m", "grapheinstein.cli", "index", tmpdir, "-o", f"{tmpdir}/graph.json"],
            capture_output=True,
            text=True,
        )
        print(f"  Exit code: {result.returncode}")
        print(f"  Stderr: {result.stderr[:200]}")
        output_exists = Path(tmpdir, "graph.json").exists()
        print(f"  Output created: {output_exists}")
        return result.returncode


def test_unreadable_directory():
    """Test indexing a directory with permission issues."""
    print("\nTesting unreadable directory...")
    with tempfile.TemporaryDirectory() as tmpdir:
        restricted = Path(tmpdir) / "restricted"
        restricted.mkdir()
        (restricted / "file.py").write_text("print('hello')")
        restricted.chmod(0o000)
        try:
            result = subprocess.run(
                [sys.executable, "-m", "grapheinstein.cli", "index", str(restricted), "-o", f"{tmpdir}/graph.json"],
                capture_output=True,
                text=True,
            )
            print(f"  Exit code: {result.returncode}")
            print(f"  Stderr: {result.stderr[:200]}")
            return result.returncode
        finally:
            restricted.chmod(0o755)


def test_invalid_output_path():
    """Test writing to an invalid output path."""
    print("\nTesting invalid output path...")
    with tempfile.TemporaryDirectory() as tmpdir:
        proj = Path(tmpdir) / "project"
        proj.mkdir()
        (proj / "test.py").write_text("print('test')")
        
        # Try to write to a path that's actually a directory
        bad_output = Path(tmpdir) / "output_dir"
        bad_output.mkdir()
        
        result = subprocess.run(
            [sys.executable, "-m", "grapheinstein.cli", "index", str(proj), "-o", str(bad_output)],
            capture_output=True,
            text=True,
        )
        print(f"  Exit code: {result.returncode}")
        print(f"  Stderr: {result.stderr[:200]}")
        return result.returncode


def test_broken_gitignore():
    """Test indexing a project with invalid .gitignore."""
    print("\nTesting broken .gitignore...")
    with tempfile.TemporaryDirectory() as tmpdir:
        proj = Path(tmpdir) / "project"
        proj.mkdir()
        (proj / "test.py").write_text("print('test')")
        # Invalid gitignore with unclosed bracket
        (proj / ".gitignore").write_text("[invalid\n")
        
        result = subprocess.run(
            [sys.executable, "-m", "grapheinstein.cli", "index", str(proj), "-o", f"{tmpdir}/graph.json"],
            capture_output=True,
            text=True,
        )
        print(f"  Exit code: {result.returncode}")
        print(f"  Stderr: {result.stderr[:200]}")
        output_exists = Path(tmpdir, "graph.json").exists()
        print(f"  Output created: {output_exists}")
        return result.returncode


def test_timeout():
    """Test indexing timeout behavior."""
    print("\nTesting timeout...")
    with tempfile.TemporaryDirectory() as tmpdir:
        proj = Path(tmpdir) / "project"
        proj.mkdir()
        # Create many files to trigger timeout
        for i in range(100):
            (proj / f"file{i}.py").write_text("print('test')\n" * 100)
        
        result = subprocess.run(
            [sys.executable, "-m", "grapheinstein.cli", "index", str(proj), 
             "-o", f"{tmpdir}/graph.json", "--config", "/dev/null"],
            capture_output=True,
            text=True,
            env={**subprocess.os.environ, "TIMEOUT_SECONDS": "1"},
        )
        print(f"  Exit code: {result.returncode}")
        print(f"  Stderr: {result.stderr[:200]}")
        return result.returncode


def test_disk_full_simulation():
    """Test behavior when output write might fail."""
    print("\nTesting output write failure...")
    with tempfile.TemporaryDirectory() as tmpdir:
        proj = Path(tmpdir) / "project"
        proj.mkdir()
        (proj / "test.py").write_text("print('test')")
        
        # Try to write to /dev/full on Linux (simulates disk full)
        result = subprocess.run(
            [sys.executable, "-m", "grapheinstein.cli", "index", str(proj), "-o", "/dev/full"],
            capture_output=True,
            text=True,
        )
        print(f"  Exit code: {result.returncode}")
        print(f"  Stderr: {result.stderr[:200]}")
        return result.returncode


if __name__ == "__main__":
    print("=== Grapheinstein Failure Scenario Tests ===\n")
    
    results = {
        "nonexistent_path": test_nonexistent_path(),
        "empty_directory": test_empty_directory(),
        "unreadable_directory": test_unreadable_directory(),
        "invalid_output_path": test_invalid_output_path(),
        "broken_gitignore": test_broken_gitignore(),
        "timeout": test_timeout(),
        "disk_full": test_disk_full_simulation(),
    }
    
    print("\n=== Summary ===")
    for test_name, exit_code in results.items():
        status = "PASS" if exit_code != 0 else "QUESTIONABLE"
        print(f"{test_name:25s}: exit={exit_code:2d} [{status}]")
    
    print("\nNotes:")
    print("- Exit code 0 for error scenarios is QUESTIONABLE")
    print("- Exit code 1 = general error")
    print("- Exit code 2 = large repo error")
    print("- Exit code 3 = timeout error")
