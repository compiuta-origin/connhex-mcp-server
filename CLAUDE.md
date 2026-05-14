# CLAUDE.md

## Project

**connhex-python** — the Python monorepo for Connhex. Hosts the SDK, the MCP server, and the CLI as sibling packages in a single uv workspace.

## Workspace layout

Three packages under `packages/`:

- `connhex-sdk` — async Connhex API client, auth, and per-domain services + schemas. No fastmcp / no server dependencies. Importable as `connhex`.
- `connhex-mcp` — the MCP server (fastmcp-based). Depends on `connhex-sdk`. Console entry point: `connhex-mcp`.
- `connhex-cli` — Typer-based CLI scaffold. Depends on `connhex-sdk`.

The workspace root `pyproject.toml` owns dev deps (pytest, ruff, pre-commit) and the single `uv.lock`. Each package has its own `pyproject.toml` and uses `uv_build`.

## Commands

```bash
uv sync                              # install workspace + dev deps
uv run pytest                        # run all tests (paths configured in root pyproject)
uv run pytest packages/connhex-sdk/tests/test_jsonapi.py::test_name   # single test
uv run ruff check . && uv run ruff format .
uv run pre-commit run --all-files

uv run connhex-mcp --mode local --transport stdio        # default local stdio
uv run connhex-mcp --mode local --transport streamable-http
uv run connhex-mcp --mode remote                          # requires CONNHEX_PUBLIC_URL
```

Python ≥ 3.11. Ruff line-length 80, target py311.

## Conventions

- Conventional Commits. Atomic where practical.
- Tests live under each package's `tests/` directory; the root `pyproject` lists them in `testpaths`.
