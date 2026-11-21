import contextlib
import contextvars
import json
import shutil
import tempfile
from pathlib import Path

_DIR = Path(__file__).parent
WORLD_PATH = _DIR / "world.json"
CLEAN_PATH = _DIR / "world.clean.json"
# Which file the functions below use. None = the shared world.json. isolated_world() sets it for the current thread only.
_active: contextvars.ContextVar = contextvars.ContextVar("world_path", default=None)


def _path() -> Path:
    return _active.get() or WORLD_PATH


@contextlib.contextmanager
def isolated_world():
    """A private copy of the clean world, used by everything that runs in this thread inside the `with`
    (load_world, save_world, reset_world, and so the tools and the firewall's rules). The shared world.json is untouched.
    Use it in a worker thread that consumes its generators itself: the setting follows the thread, not the generator."""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "world.json"
        shutil.copyfile(CLEAN_PATH, path)
        token = _active.set(path)
        try:
            yield path
        finally:
            _active.reset(token)


def load_world() -> dict:
    return json.loads(_path().read_text())


def save_world(world: dict) -> None:
    _path().write_text(json.dumps(world, indent=2) + "\n")


def reset_world() -> None:
    """Restore world.json to the pristine demo state."""
    shutil.copyfile(CLEAN_PATH, _path())
