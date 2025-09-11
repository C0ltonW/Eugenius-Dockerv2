from pathlib import Path
from typing import Dict
from .compose_builder import build_compose
from .constants import PROFILES
from .docker_cli import docker_compose_cmd
from .utils import info, fail, require_pyyaml

def write_compose_file(compose: Dict, path: Path) -> None:
    """Serialize Compose dictionary to YAML."""
    require_pyyaml()
    import yaml  # type: ignore
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(compose, f, sort_keys=False)
    info(f"Wrote {path}")

def do_generate(profile: str, env: Dict[str, str]) -> None:
    """Generate docker-compose.yaml for the requested profile."""
    compose = build_compose(env, profile)
    write_compose_file(compose, Path("docker-compose.yaml"))

def do_up(profile: str, env: Dict[str, str]) -> None:
    """Generate docker-compose.yaml and bring the stack online."""
    do_generate(profile, env)
    rc = docker_compose_cmd(["up", "-d", "--remove-orphans"])
    if rc != 0:
        fail("docker compose up failed.")
    if "nginx" in PROFILES[profile]:
        site_host = env.get("SITE_HOST", "127.0.0.1")
        app_port = env.get("APP_PORT", "81")
        info(f"Site should be reachable at: http://{site_host}:{app_port}/")
    else:
        info("Minimal profile is up (no HTTP). Use Magento CLI inside the 'php' container.")

def do_down() -> None:
    """Stop and remove the stack, including named volumes."""
    rc = docker_compose_cmd(["down", "-v"])
    if rc != 0:
        fail("docker compose down failed.")
    info("Stack stopped and volumes removed.")

def do_status() -> None:
    """Show docker compose service status."""
    rc = docker_compose_cmd(["ps"])
    raise SystemExit(rc)
