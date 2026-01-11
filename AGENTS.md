# Agent Guidelines

**Always use `uv` to run Python or manage dependencies. Never use `pip` or `python` directly.**

## Python Execution

| Task | Instead of | Use |
|------|-----------|-----|
| Run script | `python script.py` | `uv run script.py` |
| Run module | `python -m pytest` | `uv run -m pytest` |
| Install package | `pip install pkg` | `uv pip install pkg` |
| Setup environment | - | `uv sync` |
| Setup with dev deps | - | `uv sync --dev` |

## Key Rules

- Use `uv run` for all Python script/module execution
- Use `uv pip install` for package installation (or add to `pyproject.toml` and run `uv sync`)
- Use `uv sync` to install all project dependencies
- Never use bare `python`, `python3`, or `pip` commands
- All Python execution must go through `uv`
