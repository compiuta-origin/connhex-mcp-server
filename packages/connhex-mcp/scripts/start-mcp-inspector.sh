#!/usr/bin/env bash
set -euo pipefail

CONNHEX_INSTANCE_URL="${CONNHEX_INSTANCE_URL:-https://connhex.com}"
CONNHEX_AUTH_TYPE="${CONNHEX_AUTH_TYPE:-credentials}"

env_args=(
    -e "CONNHEX_INSTANCE_URL=$CONNHEX_INSTANCE_URL"
    -e "CONNHEX_AUTH_TYPE=$CONNHEX_AUTH_TYPE"
)

case "$CONNHEX_AUTH_TYPE" in
    credentials)
        : "${CONNHEX_USERNAME:?Set CONNHEX_USERNAME for auth_type=credentials}"
        : "${CONNHEX_PASSWORD:?Set CONNHEX_PASSWORD for auth_type=credentials}"
        env_args+=(-e "CONNHEX_USERNAME=$CONNHEX_USERNAME" -e "CONNHEX_PASSWORD=$CONNHEX_PASSWORD")
        ;;
    token)
        : "${CONNHEX_BEARER_TOKEN:?Set CONNHEX_BEARER_TOKEN for auth_type=token}"
        env_args+=(-e "CONNHEX_BEARER_TOKEN=$CONNHEX_BEARER_TOKEN")
        ;;
    *)
        echo "Unsupported CONNHEX_AUTH_TYPE: $CONNHEX_AUTH_TYPE" >&2
        exit 1
        ;;
esac

npx @modelcontextprotocol/inspector uv run connhex-mcp "${env_args[@]}"
