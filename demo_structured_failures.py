#!/usr/bin/env python3
"""
Demonstration of structured failure output for Librarian/automation use cases.

Shows how to parse machine-readable failure information instead of scraping stderr.
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path


def demo_large_repo_failure():
    """Demonstrate large-repo preflight failure with structured output."""
    print("\n" + "=" * 70)
    print("Demo: Large-repo preflight failure")
    print("=" * 70)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)

        # Create a config that will trigger preflight failure
        config = tmppath / "config.yaml"
        config.write_text("max_reference_scan_ops: 5\n", encoding="utf-8")

        # Create a small test repo
        repo = tmppath / "test_repo"
        repo.mkdir()
        (repo / "a.py").write_text("import b\n")
        (repo / "b.py").write_text("def foo(): pass\n")
        (repo / "c.py").write_text("from b import foo\n")

        output = tmppath / "graph.json"
        failure_file = tmppath / "graph.json.failure.json"

        # Run grapheinstein
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "grapheinstein",
                "index",
                str(repo),
                "--config",
                str(config),
                "-o",
                str(output),
            ],
            capture_output=True,
            text=True,
        )

        print(f"Exit code: {result.returncode}")
        print(f"Output exists: {output.exists()}")
        print(f"Failure file exists: {failure_file.exists()}")

        if failure_file.exists():
            print("\nStructured failure output:")
            failure_info = json.loads(failure_file.read_text())
            print(json.dumps(failure_info, indent=2))

            # Example: Parse for automation
            print("\n--- Automation-friendly parsing ---")
            print(f"Category: {failure_info['error_category']}")
            print(f"Exit code: {failure_info['exit_code']}")

            if "details" in failure_info:
                details = failure_info["details"]
                if "failure_codes" in details:
                    print(f"Failure codes: {', '.join(details['failure_codes'])}")
                if "metrics" in details:
                    print(f"Metrics: {details['metrics']}")
                if "suggested_flags" in details:
                    print(f"Suggested flags: {', '.join(details['suggested_flags'])}")
        else:
            print("\nStderr:")
            print(result.stderr)


def demo_config_error():
    """Demonstrate config error with structured output."""
    print("\n" + "=" * 70)
    print("Demo: Configuration error")
    print("=" * 70)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)

        # Create an invalid config
        config = tmppath / "bad_config.yaml"
        config.write_text("languages: [nosuchlang]\n", encoding="utf-8")

        repo = tmppath / "test_repo"
        repo.mkdir()
        (repo / "test.py").write_text("print('hello')\n")

        output = tmppath / "graph.json"
        failure_file = tmppath / "graph.json.failure.json"

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "grapheinstein",
                "index",
                str(repo),
                "--config",
                str(config),
                "-o",
                str(output),
            ],
            capture_output=True,
            text=True,
        )

        print(f"Exit code: {result.returncode}")

        if failure_file.exists():
            print("\nStructured failure output:")
            failure_info = json.loads(failure_file.read_text())
            print(f"Category: {failure_info['error_category']}")
            print(f"Message: {failure_info['error_message']}")


def demo_successful_index():
    """Demonstrate that successful indexing does not write failure file."""
    print("\n" + "=" * 70)
    print("Demo: Successful indexing")
    print("=" * 70)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)

        repo = tmppath / "test_repo"
        repo.mkdir()
        (repo / "main.py").write_text("def main():\n    print('Hello')\n")

        output = tmppath / "graph.json"
        failure_file = tmppath / "graph.json.failure.json"

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "grapheinstein",
                "index",
                str(repo),
                "-o",
                str(output),
            ],
            capture_output=True,
            text=True,
        )

        print(f"Exit code: {result.returncode}")
        print(f"Output exists: {output.exists()}")
        print(f"Failure file exists: {failure_file.exists()}")

        if output.exists():
            graph = json.loads(output.read_text())
            print(f"Graph nodes: {len(graph['nodes'])}")


def main():
    print("STRUCTURED FAILURE OUTPUT DEMONSTRATION")
    print("=" * 70)
    print("This demonstrates machine-readable failure reporting for")
    print("automation tools like Lursa Librarian.")

    demo_large_repo_failure()
    demo_config_error()
    demo_successful_index()

    print("\n" + "=" * 70)
    print("Summary:")
    print("- Failures write <output>.failure.json with structured data")
    print("- Success does not write failure file")
    print("- Automation can parse failure details instead of stderr")
    print("=" * 70)


if __name__ == "__main__":
    main()
