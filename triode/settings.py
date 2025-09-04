# triode/settings.py
import json
from pathlib import Path
from typing import Any, Dict

DEFAULTS = {
    "browser": {"engine": None},  # None => default_engine
    "terminal": {"shell": None}
}

def _config_path() -> Path:
    base = Path.home() / ".config" / "triode"
    base.mkdir(parents=True, exist_ok=True)
    return base / "config.json"

def load_settings() -> Dict[str, Any]:
    p = _config_path()
    if not p.exists():
        p.write_text(json.dumps(DEFAULTS, indent=2))
        return DEFAULTS.copy()
    return json.loads(p.read_text())

def save_settings(data: Dict[str, Any]) -> None:
    p = _config_path()
    p.write_text(json.dumps(data, indent=2))
