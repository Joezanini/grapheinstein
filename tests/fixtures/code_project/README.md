# Code project fixture for Tree-sitter extraction tests

Expected entities (1-based start lines):

## src/app.py
- `greet` function at line 1
- `Greeter` class at line 5
- `Greeter.hello` method at line 6

## src/main.py
- `run` function at line 4
- imports `app` / `greet` from app
- calls `greet` from `run`

## src/util.go
- `Add` function at line 3

## broken/bad.py
- Intentionally invalid Python (syntax error)

## notes.txt
- Unsupported extension (no code entities)

## ignored_dir/secret.py
- Ignored via .gitignore
