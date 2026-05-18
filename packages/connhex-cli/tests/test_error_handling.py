from connhex.errors import ConnhexAPIError
from typer.testing import CliRunner

from connhex_cli.commands import things as things_cmd
from connhex_cli.main import app

runner = CliRunner()


class FakeThings:
    def get_flapping(self, **kwargs):
        raise ConnhexAPIError(
            status=404,
            detail="Requested url does not match any rules",
        )


class FakeConnhex:
    things = FakeThings()


def test_api_errors_render_without_traceback(monkeypatch):
    monkeypatch.setattr(things_cmd, "connhex_client", lambda ctx: FakeConnhex())

    result = runner.invoke(app, ["things", "flapping"])

    assert result.exit_code == 1
    assert (
        "Error: Connhex API returned 404: "
        "Requested url does not match any rules"
    ) in result.output
    assert "Traceback" not in result.output


def test_debug_reraises_api_errors(monkeypatch):
    monkeypatch.setattr(things_cmd, "connhex_client", lambda ctx: FakeConnhex())

    result = runner.invoke(app, ["--debug", "things", "flapping"])

    assert result.exit_code == 1
    assert isinstance(result.exception, ConnhexAPIError)
