import subprocess
from pathlib import Path
from typing import Dict
from .compose_builder import build_compose
from .constants import PROFILES
from .docker_cli import docker_compose_cmd
from .utils import info, fail, require_pyyaml


def _is_running(service: str) -> bool:
    # returns True if container exists & is running
    rc = subprocess.call(["docker", "compose", "ps", "-q", service],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return rc == 0

def _exec(cmd: str) -> int:
    return subprocess.call(["bash", "-lc", cmd])


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

def do_magento_setup(env: Dict[str, str], reset: bool = False, with_sample: bool = False) -> None:
    """
    Idempotent installer:
      - Requires stack running (php, db, search).
      - Skips if app/etc/env.php exists.
      - Optional --reset uninstalls first.
    """
    # 1. Ensure stack is up (php container must exist)
    if not _is_running("php"):
        info("Stack is not running; bringing it up (full profile).")
        # Bring up the full profile by default
        # from .commands import do_up   # reuse existing up impl
        do_up("full", env)
    else:
        info("Stack detected as running.")

    site_host = env.get("SITE_HOST", "127.0.0.1")
    app_port  = env.get("APP_PORT", "81")
    db_name   = env.get("MYSQL_DATABASE", "magento")
    db_user   = env.get("MYSQL_USER", "magento")
    db_pass   = env.get("MYSQL_PASSWORD", "magento")

    # 2. Quick readiness checks (DB + search respond to TCP)
    info("Waiting for DB and Search to be reachable...")
    wait_cmd = r"""
      set -e
      # wait for DB :3306
      for i in {1..60}; do nc -zv db 3306 >/dev/null 2>&1 && break || sleep 2; done
      # wait for search :9200
      for i in {1..60}; do nc -zv search 9200 >/dev/null 2>&1 && break || sleep 2; done
    """
    rc = subprocess.call(["docker", "compose", "exec", "-T", "php", "bash", "-lc", wait_cmd])
    if rc != 0:
        fail("DB/Search were not reachable in time.")

    # 3. If env.php exists and not resetting, bail out politely
    check_cmd = r"test -f /var/www/html/app/etc/env.php"
    rc = subprocess.call(["docker", "compose", "exec", "-T", "php", "bash", "-lc", check_cmd])
    if rc == 0 and not reset:
        info("Magento already installed (app/etc/env.php found). Nothing to do.")
        info(f"Open: http://{site_host}:{app_port}/")
        return

    # Optional reset(uninstall)
    if reset:
        info("Reset requested: running 'bin/magento setup:uninstall' (drops tables).")
        uninstall = r"""
              set -e
              cd /var/www/html || exit 1
              if [ -f bin/magento ]; then
                php -d detect_unicode=0 bin/magento setup:uninstall -n || true
              fi
              rm -rf var/* generated/* pub/static/* app/etc/env.php
            """
        subprocess.call(["docker", "compose", "exec", "-T", "php", "bash", "-lc", uninstall])

    # 4. Create Project if missing
    create_project = r"""
          set -e
          cd /var/www/html
          if [ ! -f composer.json ]; then
            composer create-project --repository-url=https://repo.mage-os.org/ mage-os/project-community-edition .
          fi
        """
    rc = subprocess.call(["docker", "compose", "exec", "-T", "php", "bash", "-lc", create_project])
    if rc != 0:
        fail("Composer create-project failed.")

    # 5. Install (Elasticsearch 7 wire protocol; adjust if you switch to OpenSearch)
    install = fr"""
          set -e
          cd /var/www/html
          php -d detect_unicode=0 bin/magento setup:install \
            --base-url="http://{site_host}:{app_port}/" \
            --db-host=db --db-name={db_name} --db-user={db_user} --db-password={db_pass} \
            --backend-frontname=admin \
            --admin-firstname=Admin --admin-lastname=User \
            --admin-email=admin@example.com --admin-user=admin --admin-password=Admin123! \
            --language=en_US --currency=USD --timezone=America/New_York \
            --use-rewrites=1 \
            --search-engine=elasticsearch7 \
            --elasticsearch-host=search --elasticsearch-port=9200
        """
    rc = subprocess.call(["docker", "compose", "exec", "-T", "php", "bash", "-lc", install])
    if rc != 0:
        fail("Magento setup:install failed. If database has old tables, re-run with --reset.")


    # 6. Post-install housekeeping
    post = r"""
      set -e
      cd /var/www/html
      bin/magento cache:flush
      bin/magento indexer:reindex
    """
    subprocess.call(["docker", "compose", "exec", "-T", "php", "bash", "-lc", post])
    info(f"Done. Open: http://{site_host}:{app_port}/")
