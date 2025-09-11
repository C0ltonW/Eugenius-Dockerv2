import os
import sys
from pathlib import Path
from typing import Dict

def info(msg: str) -> None:
    print(f"[INFO] {msg}")

def warn(msg: str) -> None:
    print(f"[WARN] {msg}")

def fail(msg: str) -> None:
    print(f"[ERROR] {msg}")
    sys.exit(1)

def require_pyyaml() -> None:
    try:
        import yaml  # noqa: F401
    except ImportError:
        fail("Missing dependency 'PyYAML'. Install with: pip install pyyaml")

def is_wsl() -> bool:
    try:
        return "microsoft" in Path("/proc/version").read_text(encoding="utf-8").lower()
    except FileNotFoundError:
        return False

def preflight(env: Dict[str, str], profile: str) -> None:
    """
    Windows/WSL guidance before bringing stack up:
     - Warn if project appears on Windows path (bind mount perf).
     - Remind vm.max_map_count when using OpenSearch/Elasticsearch on Windows/WSL2.
    """
    project_root = Path(".").resolve()
    root = str(project_root).lower()
    on_windows = os.name == "nt"
    on_wsl = is_wsl()

    # Bind-mount performance
    if on_windows or root.startswith("/mnt/"):
        in_wsl_fs = root.startswith("\\\\wsl$") or (on_wsl and not root.startswith("/mnt/"))
        if not in_wsl_fs:
            warn("Your project appears to be on a Windows path.")
            warn("For faster bind mounts & reliable file watching, move the repo into your WSL distro")
            warn("(e.g., ~/projects/...) and run the orchestrator from a WSL shell.")
            warn("Docs: https://docs.docker.com/desktop/features/wsl/best-practices/")

    # vm.max_map_count reminder for search engines
    search_img = (env.get("SEARCH_IMAGE", "")).lower()
    uses_search = profile in ("minimal", "full")
    if uses_search and ("opensearch" in search_img or "elasticsearch" in search_img):
        if on_windows or on_wsl:
            info("Reminder (Windows/WSL2): set vm.max_map_count=262144 before starting search:")
            info("  PowerShell → wsl -d docker-desktop sysctl -w vm.max_map_count=262144")
            info("  (Persist via C:\\Users\\<you>\\.wslconfig if desired)")
