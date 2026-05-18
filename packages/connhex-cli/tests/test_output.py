from pydantic import BaseModel

from connhex_cli.output import render


class Row(BaseModel):
    id: str
    tenant: str | None = None


def test_table_render_handles_model_rows_with_missing_keys(capsys):
    render([Row(id="one", tenant="a"), Row(id="two")], "table")

    output = capsys.readouterr().out
    assert "one" in output
    assert "two" in output
    assert "tenant" in output


def test_table_render_handles_dict_rows_with_missing_keys(capsys):
    render([{"id": "one", "tenant": "a"}, {"id": "two"}], "table")

    output = capsys.readouterr().out
    assert "one" in output
    assert "two" in output
    assert "tenant" in output
