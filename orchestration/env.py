from pathlib import Path
from typing import Dict
import re

from .utils import info
from .constants import DEFAULT_ENV


def _strip_quotes(v: str) -> str:
    if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
        return v[1:-1]
    return v


def load_env(env_path: Path) -> Dict[str, str]:
    """
    Minimal KEY=VALUE .env loader.

    - Ignores comments/blank lines.
    - Allows lines prefixed with 'export '.
    - Strips surrounding single/double quotes from values.
    - Strips inline comments from *unquoted* values only (e.g., VALUE # note).
      If the value is quoted, we preserve everything inside the quotes.
    """
    env: Dict[str, str] = {}
    if not env_path.exists():
        return env

    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[len("export "):].lstrip()

        key, val = line.split("=", 1)
        key = key.strip()
        val = val.strip()

        is_quoted = (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'"))
        if not is_quoted:
            # Strip inline comment only for unquoted values:
            # match the first " #..." sequence after some whitespace.
            parts = re.split(r"\s+#", val, maxsplit=1)
            val = parts[0].rstrip()

        env[key] = _strip_quotes(val)

    return env


def ensure_env_file(env_path: Path) -> None:
    """
    Create .env if missing.

    Preference order:
      1) ./templates/env.default (if present)
      2) constants.DEFAULT_ENV

    Never overwrite existing .env.
    """
    if env_path.exists():
        return

    template_path = Path("./templates/env.default")
    if template_path.exists():
        env_path.write_text(template_path.read_text(encoding="utf-8"), encoding="utf-8")
        info(f"Created {env_path} from template {template_path}")
        return

    env_path.write_text(DEFAULT_ENV, encoding="utf-8")
    info(f"Created default .env at {env_path} (from constants)")
