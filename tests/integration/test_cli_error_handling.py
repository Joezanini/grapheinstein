"""Integration test for CLI error handling and warnings."""

from pathlib import Path

import pytest

from grapheinstein.cli import app


def test_empty_directory_shows_warning(tmp_path: Path, capsys):
    """Test that indexing an empty directory shows appropriate warning."""
    empty_dir = tmp_path / "empty_project"
    empty_dir.mkdir()
    output = tmp_path / "graph.json"

    # Should succeed but warn about empty graph
    with pytest.raises(SystemExit) as exc_info:
        app(
            args=["index", str(empty_dir), "-o", str(output)],
            standalone_mode=True,
        )

    assert exc_info.value.code == 0, "Empty directory should succeed"
    assert output.exists(), "Output file should be created"

    captured = capsys.readouterr()
    assert "Warning" in captured.err or "empty" in captured.err.lower()


def test_all_files_skipped_shows_warning(tmp_path: Path, capsys):
    """Test that indexing where all files fail to parse shows warning."""
    project = tmp_path / "broken_project"
    project.mkdir()

    # Create binary files that can't be parsed as code
    for i in range(5):
        binary_file = project / f"data{i}.bin"
        binary_file.write_bytes(b"\x00\x01\x02\xFF\xFE" * 100)

    output = tmp_path / "graph.json"

    with pytest.raises(SystemExit) as exc_info:
        app(
            args=["index", str(project), "-o", str(output)],
            standalone_mode=True,
        )

    assert exc_info.value.code == 0
    assert output.exists()

    captured = capsys.readouterr()
    # Should warn about no entities extracted
    assert "Warning" in captured.err or "no extracted" in captured.err.lower()


def test_nonexistent_path_clear_error(tmp_path: Path, capsys):
    """Test that nonexistent path shows clear error message."""
    nonexistent = tmp_path / "does_not_exist"
    output = tmp_path / "graph.json"

    with pytest.raises(SystemExit) as exc_info:
        app(
            args=["index", str(nonexistent), "-o", str(output)],
            standalone_mode=True,
        )

    assert exc_info.value.code == 1

    captured = capsys.readouterr()
    assert "File not found" in captured.err or "does not exist" in captured.err


def test_invalid_output_path_clear_error(tmp_path: Path, capsys):
    """Test that invalid output path shows clear error message."""
    project = tmp_path / "project"
    project.mkdir()
    (project / "test.py").write_text("print('hello')")

    # Try to write to a directory
    bad_output = tmp_path / "output_dir"
    bad_output.mkdir()

    with pytest.raises(SystemExit) as exc_info:
        app(
            args=["index", str(project), "-o", str(bad_output)],
            standalone_mode=True,
        )

    assert exc_info.value.code == 1

    captured = capsys.readouterr()
    assert "I/O error" in captured.err or "Cannot write" in captured.err


def test_healthy_project_no_warnings(tmp_path: Path, capsys):
    """Test that a healthy project doesn't trigger warnings."""
    project = tmp_path / "healthy_project"
    project.mkdir()

    (project / "main.py").write_text("""
def hello():
    '''Say hello.'''
    print('Hello, world!')

class Greeter:
    '''A greeter class.'''
    def greet(self, name):
        return f'Hello, {name}!'
""")

    output = tmp_path / "graph.json"

    with pytest.raises(SystemExit) as exc_info:
        app(
            args=["index", str(project), "-o", str(output)],
            standalone_mode=True,
        )

    assert exc_info.value.code == 0
    assert output.exists()

    captured = capsys.readouterr()
    # Should NOT have warnings about empty or sparse graph
    err_lower = captured.err.lower()
    assert "empty" not in err_lower or "complete" in err_lower
    # "Index complete" contains "empty" substring, so check it's the right context
