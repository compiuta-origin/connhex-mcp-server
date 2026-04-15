# Connhex MCP Server

An MCP server that exposes [Connhex](https://connhex.com) APIs as tools.

## Setup

### Prerequisites

- Python 3.11+
- A Connhex account with access to your instance

### Configure your MCP client

Add the server to your MCP client configuration.

**Claude Desktop** (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "connhex": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/compiuta-origin/connhex-mcp-server",
        "connhex-mcp"
      ],
      "env": {
        "CONNHEX_INSTANCE_URL": "<connhex-instance-url>",
        "CONNHEX_USERNAME": "your-email@example.com",
        "CONNHEX_PASSWORD": "your-password"
      }
    }
  }
}
```

### Authentication

The server requires `CONNHEX_INSTANCE_URL` pointing to your Connhex instance.

Authentication is configured via `CONNHEX_AUTH_TYPE` (defaults to `credentials`):

| Auth type     | Required env vars                         | Description                        |
| ------------- | ----------------------------------------- | ---------------------------------- |
| `credentials` | `CONNHEX_USERNAME`, `CONNHEX_PASSWORD`    | Logs in with username and password |
| `token`       | `CONNHEX_BEARER_TOKEN`                    | Uses a static bearer token         |
| `session`     | _(none — provided via transport headers)_ | Forwards session from the client   |

### Transport

By default the server uses `stdio`. You can select a different transport by appending `--transport` to the `args` array:

```json
"args": [
  "--from",
  "git+https://github.com/compiuta-origin/connhex-mcp-server",
  "connhex-mcp",
  "--transport",
  "streamable-http"
]
```

Available transports: `stdio`, `http`, `sse`, `streamable-http`.

## Updating

`uvx` caches the built environment on first run and does **not** re-fetch the git repo on subsequent invocations, so updates to this server are not picked up automatically. To pull the latest version, run:

```bash
uvx --refresh --from git+https://github.com/compiuta-origin/connhex-mcp-server connhex-mcp
```

Then restart your MCP client.

## Usage Examples

Once the MCP server is connected, you can ask your AI assistant things like:

- "Who am I logged in as?"
- "List all my resources of type `<type>`"
- "Show me the last 10 messages from thing `<thing-id>`"
- "Read messages from channel `<channel-id>` between yesterday and today"

## Testing with MCP Inspector

You can test the server locally using [MCP Inspector](https://github.com/modelcontextprotocol/inspector) (requires Node.js):

```bash
export CONNHEX_INSTANCE_URL=<connhex-instance-url>
export CONNHEX_USERNAME=your-email@example.com
export CONNHEX_PASSWORD=your-password
./scripts/start-mcp-inspector.sh
```

For token-based auth:

```bash
export CONNHEX_INSTANCE_URL=<connhex-instance-url>
export CONNHEX_AUTH_TYPE=token
export CONNHEX_BEARER_TOKEN=your-token
./scripts/start-mcp-inspector.sh
```

This opens a browser UI where you can interactively call tools and inspect responses.

## Development

Clone the repo and install dependencies:

```bash
git clone https://github.com/compiuta-origin/connhex-mcp-server.git
cd connhex-mcp-server
uv sync --dev
```

Run the server locally:

```bash
uv run connhex-mcp
```

Run tests and linting:

```bash
uv run pytest
uv run ruff check .
```
