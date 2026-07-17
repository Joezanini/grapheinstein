# Fixture expectations

When indexed with `--include-docs` / `--include-pdfs`:

- `docs/guide.md`: H1 Guide, H2 Installation, H3 Steps; mentions `README.md`
- `docs/notes.txt`: underlined Notes, Details
- `docs/overview.rst`: Overview, Getting Started
- `manuals/sample.pdf`: multi-section (TOC)
- `manuals/corrupt.pdf`: must skip without aborting
- `ignored_docs/secret.md`: ignored — no headings
