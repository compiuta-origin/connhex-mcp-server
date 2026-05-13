# Connhex SDK

Internal async Python client for the Connhex API.

## What it provides

- Authentication (Kratos password login, bearer token, session forwarding)
- Per-domain async service classes: `ThingsService`, `ModelsService`, `ReaderService`, `ResourcesService`, `RulesEngineService`, `IAMService`, ...
- Pydantic models for all API responses
- A shared `ConnhexClient` that handles auth resolution and HTTP retries
