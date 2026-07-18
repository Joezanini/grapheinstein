import importlib.util

from typer.testing import CliRunner

from grapheinstein.cli import _KNOWN_COMMANDS, cli

runner = CliRunner()


def test_known_commands_includes_serve():
    assert "serve" in _KNOWN_COMMANDS


def test_serve_help_documents_port_host_and_docs():
    result = runner.invoke(cli, ["serve", "--help"])
    assert result.exit_code == 0
    assert "--port" in result.output
    assert "8000" in result.output
    assert "--host" in result.output
    assert "127.0.0.1" in result.output or "loopback" in result.output.lower()
    assert "docs/agent-integration.md" in result.output


def test_serve_missing_extras_exits_nonzero(monkeypatch):
    import grapheinstein.serve as serve_mod

    def boom(*_a, **_k):
        raise serve_mod.ServeExtrasError(
            "Local HTTP serve requires optional extras "
            "(missing: fastapi). Install with: pip install 'grapheinstein[serve]'"
        )

    monkeypatch.setattr(serve_mod, "run_server", boom)
    result = runner.invoke(cli, ["serve", "--port", "8765"])
    assert result.exit_code != 0
    assert "grapheinstein[serve]" in result.output


def test_serve_deps_findable_when_extras_installed():
    if importlib.util.find_spec("fastapi") is None:
        return  # optional; contract still covered by missing-extras test
    from grapheinstein.serve import ensure_serve_deps

    ensure_serve_deps()
