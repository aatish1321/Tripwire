import json
import shutil
from pathlib import Path

_DIR = Path(__file__).parent
WORLD_PATH = _DIR / "world.json"
CLEAN_PATH = _DIR / "world.clean.json"


def load_world() -> dict:
    return json.loads(WORLD_PATH.read_text())


def save_world(world: dict) -> None:
    WORLD_PATH.write_text(json.dumps(world, indent=2) + "\n")


def reset_world() -> None:
    """Restore world.json to the pristine demo state."""
    shutil.copyfile(CLEAN_PATH, WORLD_PATH)
