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

## Available Tools

### IAM

| Tool     | Description                                                |
| -------- | ---------------------------------------------------------- |
| `whoami` | Return information about the currently authenticated user. |

### Resources (JSON:API)

Generic CRUD over the Connhex resources service.

| Tool              | Description                                                                                                        |
| ----------------- | ------------------------------------------------------------------------------------------------------------------ |
| `list_resources`  | List resources of a given type, with filtering, sorting, sparse fieldsets, and pagination.                         |
| `get_resource`    | Get a specific resource by ID.                                                                                     |
| `create_resource` | Create a new resource.                                                                                             |
| `update_resource` | Partially update an existing resource.                                                                             |
| `delete_resource` | Delete a resource (irreversible).                                                                                  |
| `get_schema`      | Discover valid resource types, attributes, and relationships across both the resources and manufacturing services. |

### Manufacturing (JSON:API)

Same CRUD shape as Resources, against the manufacturing service.

| Tool                            | Description                                     |
| ------------------------------- | ----------------------------------------------- |
| `list_manufacturing_resources`  | List manufacturing resources.                   |
| `get_manufacturing_resource`    | Get a manufacturing resource by ID.             |
| `create_manufacturing_resource` | Create a manufacturing resource.                |
| `update_manufacturing_resource` | Partially update a manufacturing resource.      |
| `delete_manufacturing_resource` | Delete a manufacturing resource (irreversible). |

### Reader (IoT messages)

Read messages from Connhex IoT channels. Supports the four CMP components (`messages`, `params`, `infos`, `metrics`) and decimation/aggregation for SenML formats.

| Tool                    | Description                                                                                            |
| ----------------------- | ------------------------------------------------------------------------------------------------------ |
| `read_channel_messages` | Read messages from a channel by its channel ID.                                                        |
| `read_thing_messages`   | Read messages for a thing by its Connhex thing ID (resolves the channel ID from the thing's metadata). |

### Rules Engine

Manage rules and inspect triggered rule events.

| Tool               | Description                                    |
| ------------------ | ---------------------------------------------- |
| `list_rules`       | List rules, with filtering and pagination.     |
| `get_rule`         | Get a single rule by ID.                       |
| `create_rule`      | Create a new rule.                             |
| `update_rule`      | Partially update an existing rule.             |
| `delete_rule`      | Delete a rule (irreversible).                  |
| `list_rule_events` | List rule events (triggered rule occurrences). |

## Usage Examples

**Identity**

- "Who am I logged in as?"

**Discover the data model**

- "What resource types are available in this Connhex instance?"
- "What attributes does the `devices` resource type have?"

**Browse and search resources**

- "List all my devices."
- "Find devices whose serial starts with `ABC`."
- "Show me plants created in the last week."
- "Get device `<device-id>` and include its related site."
- "List the 50 most recently created devices, only showing `serial` and `name`."

**Create / update / delete resources**

- "Create a new installation called `Installation A`."
- "Update device `<device-id>` to set its name to `Boiler 3`."
- "Delete installation `<installation-id>`."

**Manufacturing**

- "List all manufacturing batches."

**IoT messages (telemetry)**

- "Show me the last 10 messages from thing `<thing-id>`."
- "Read messages from channel `<channel-id>` between yesterday and today."
- "Show me the daily max CPU usage (metrics) for device `<thing-id>` this week."
- "Filter messages from channel `<channel-id>` to only the `temperature` SenML name."

**Rules Engine**

- "List all enabled rules with severity `critical`."
- "Show me rule `<rule-id>`."
- "Disable rule `<rule-id>`."
- "Show me all rule events from the last 24 hours."
- "List events triggered by rule `<rule-id>` between `<from>` and `<to>`."

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
