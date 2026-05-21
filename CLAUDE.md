# CLAUDE.md
This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Environment

- Python 3.13, managed with [uv](https://docs.astral.sh/uv/)
- Dependencies declared in `pyproject.toml`; lockfile is `uv.lock`

## Commands

```bash
# Install dependencies
uv sync

# Run the project
uv run python <script.py>

# Add a dependency
uv add <package>
```

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full system design.
