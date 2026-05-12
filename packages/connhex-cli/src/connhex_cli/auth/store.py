import json
import os
import stat
import tempfile
from pathlib import Path

from connhex_cli.auth.models import StoredCreds


def _creds_path() -> Path:
    return Path.home() / ".connhex" / "credentials.json"


def load() -> StoredCreds | None:
    path = _creds_path()
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
        return StoredCreds(**data)
    except Exception:
        return None


def save(creds: StoredCreds) -> Path:
    path = _creds_path()
    first_save = not path.exists()

    path.parent.mkdir(parents=True, exist_ok=True)

    fd, tmp_path = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(creds.model_dump_json(indent=2))
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise

    try:
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        pass

    if first_save:
        import typer

        typer.echo(
            f"Credentials cached in plaintext at {path}. "
            "Run `connhex logout` to clear.",
            err=True,
        )

    return path


def clear() -> bool:
    path = _creds_path()
    if not path.exists():
        return False
    path.unlink()
    return True
