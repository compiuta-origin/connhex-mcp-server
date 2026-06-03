# Connhex SDK

Internal async Python client for the Connhex API.

## What it provides

- Authentication (Kratos password login, bearer token, session forwarding)
- Per-domain async service classes: `ThingsService`, `ModelsService`, `ReaderService`, `ResourcesService`, `RulesEngineService`, `IAMService`, ...
- Pydantic models for all API responses
- A shared `ConnhexClient` that handles auth resolution and HTTP retries

## Instance URL

SDK clients target the Connhex SaaS instance at `https://connhex.com` by default:

```python
from connhex import AsyncConnhex

async with AsyncConnhex(token="ory_st_...") as connhex:
    me = await connhex.iam.whoami()
```

Override the instance URL for staging, private, or self-hosted deployments:

```python
from connhex import Connhex

with Connhex(
    instance_url="https://staging.connhex.example",
    token="ory_st_...",
) as connhex:
    things = connhex.things.list()
```

Precedence is: explicit `instance_url`, then `CONNHEX_INSTANCE_URL`, then `https://connhex.com`.
