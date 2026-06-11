# Connhex Tools

Tools workspace for [Connhex](https://connhex.com). Contains the MCP server,
the CLI, and the API SDK as sibling packages in a single
[uv workspace](https://docs.astral.sh/uv/concepts/workspaces/).

## Packages

| Package                                | Description                                                                     | README                              |
| -------------------------------------- | ------------------------------------------------------------------------------- | ----------------------------------- |
| [`connhex-sdk`](packages/connhex-sdk/) | Async Python client for the Connhex API. Used internally by the other packages. | [→](packages/connhex-sdk/README.md) |
| [`connhex-mcp`](packages/connhex-mcp/) | MCP server that exposes Connhex APIs as tools for AI clients (Claude, etc.).    | [→](packages/connhex-mcp/README.md) |
| [`connhex-cli`](packages/connhex-cli/) | Command-line interface for managing connhex resources.                          | [→](packages/connhex-cli/README.md) |

## Getting started

**Prerequisites:** Python 3.11+, [uv](https://docs.astral.sh/uv/getting-started/installation/).

```bash
git clone https://github.com/compiuta-origin/connhex-tools.git
cd connhex-tools
uv sync
```

This installs all three packages and their dependencies into a shared `.venv`.

## Development

```bash
uv run pytest                        # run all tests
uv run ruff check . && uv run ruff format .
uv run pre-commit run --all-files
```

Run a specific package's tests:

```bash
uv run pytest packages/connhex-cli/tests
```
