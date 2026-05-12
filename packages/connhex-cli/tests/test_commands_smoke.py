"""Smoke tests: ensure --help works on every subcommand without error."""

import pytest
from typer.testing import CliRunner

from connhex_cli.main import app

runner = CliRunner()

SUBCOMMANDS = [
    ["--help"],
    ["auth", "--help"],
    ["auth", "login", "--help"],
    ["auth", "logout", "--help"],
    ["auth", "whoami", "--help"],
    ["auth", "status", "--help"],
    ["things", "--help"],
    ["things", "list", "--help"],
    ["things", "get", "--help"],
    ["things", "status", "--help"],
    ["things", "status-summary", "--help"],
    ["things", "flapping", "--help"],
    ["things", "uptime", "--help"],
    ["things", "channels", "--help"],
    ["models", "--help"],
    ["models", "list", "--help"],
    ["models", "get", "--help"],
    ["models", "things", "--help"],
    ["resources", "--help"],
    ["resources", "list", "--help"],
    ["resources", "get", "--help"],
    ["resources", "create", "--help"],
    ["resources", "update", "--help"],
    ["resources", "delete", "--help"],
    ["rules", "--help"],
    ["rules", "list", "--help"],
    ["rules", "get", "--help"],
    ["rules", "create", "--help"],
    ["rules", "update", "--help"],
    ["rules", "delete", "--help"],
    ["rules", "events", "--help"],
    ["messages", "--help"],
    ["messages", "channel", "--help"],
    ["messages", "thing", "--help"],
]


@pytest.mark.parametrize(
    "args", SUBCOMMANDS, ids=[" ".join(a) for a in SUBCOMMANDS]
)
def test_help(args):
    result = runner.invoke(app, args)
    assert result.exit_code == 0, (
        f"Command {args} failed with exit_code={result.exit_code}:\n{result.output}"
    )
