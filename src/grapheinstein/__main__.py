"""Allow `python -m grapheinstein`."""

from grapheinstein.cli import app

if __name__ == "__main__":
    app()  # argv-rewriting entry (supports bare project path)
