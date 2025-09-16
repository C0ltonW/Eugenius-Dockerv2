# orchestration/commands.py
import subprocess
from pathlib import Path
from typing import Dict

from .compose_builder import build_compose
from .constants import PROFILES
from .docker_cli import docker_compose_cmd
from .utils import info, fail, require_pyyaml, warn


def _is_running(service: str) -> bool:
    # returns True if container exists & is running
    rc = subprocess.call(
        ["docker", "compose", "ps", "-q", service],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return rc == 0


def _exec(cmd: str) -> int:
    return subprocess.call(["bash", "-lc", cmd])


def _dc_exec(cmd: str) -> int:
    return subprocess.call(["docker", "compose", "exec", "-T", "php", "bash", "-lc", cmd])


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


# orchestration/commands.py (inside do_magento_setup)

def do_magento_setup(env: Dict[str, str], reset: bool = False, with_sample: bool = False) -> None:
    # 1) Ensure stack is up
    if not _is_running("php"):
        info("Stack is not running; bringing it up (full profile).")
        do_up("full", env)
    else:
        info("Stack detected as running.")

    site_host = env.get("SITE_HOST", "127.0.0.1")
    app_port = env.get("APP_PORT", "81")
    db_name = env.get("MYSQL_DATABASE", "magento")
    db_user = env.get("MYSQL_USER", "magento")
    db_pass = env.get("MYSQL_PASSWORD", "magento")

    # 2) Wait for DB/Search
    info("Waiting for DB and Search to be reachable...")
    wait_cmd = r"""
        set -e
        for i in {1..60}; do nc -zv db 3306 >/dev/null 2>&1 && break || sleep 2; done
        for i in {1..60}; do nc -zv search 9200 >/dev/null 2>&1 && break || sleep 2; done
        """
    if _dc_exec(wait_cmd) != 0:
        fail("DB/Search were not reachable in time.")

    # 3) If already installed and not resetting, exit gracefully
    if _dc_exec("test -f /var/www/html/app/etc/env.php") == 0 and not reset:
        info("Magento already installed (app/etc/env.php found). Nothing to do.")
        info(f"Open: http://{site_host}:{app_port}/")
        return

    # 4) Optional uninstall/reset
    if reset:
        info("Reset requested: uninstalling & cleaning webroot...")
        uninstall = r"""
        set -e
        cd /var/www/html
        if [ -f bin/magento ]; then
          php -d detect_unicode=0 bin/magento setup:uninstall -n || true
        fi
        rm -rf var/* generated/* pub/static/* app/etc/env.php vendor
        """
        _dc_exec(uninstall)
        full_clean = r"""
        set -e
        cd /var/www/html
        shopt -s dotglob
        rm -rf -- *
        """
        _dc_exec(full_clean)

    # 5) Prepare webroot
    prep = r"""
        set -e
        cd /var/www/html
        # remove tiny phpinfo stub if present
        if [ -f index.php ] && [ "$(wc -c < index.php)" -lt 64 ] && grep -q 'phpinfo' index.php; then
          rm -f index.php
        fi
        # refuse to clone into a non-empty dir (safety)
        if [ ! -f composer.json ] && [ "$(ls -A | wc -l)" -gt 0 ]; then
          echo "Refusing to run Git clone in a non-empty directory."
          echo "Move/remove files under ./src or run with --reset."
          exit 11
        fi
        """
    if _dc_exec(prep) != 0:
        fail("Webroot not suitable for Git clone (see message above).")

    # 6) Create project (Git only)
    create_project = r"""
        set -e
        cd /var/www/html
        if [ ! -f composer.json ]; then
          git clone --depth=1 https://github.com/mage-os/mageos-magento2.git .
          # trust the mount path before Composer
          git config --global --add safe.directory /var/www/html || true
          composer install --no-interaction --prefer-dist
        fi
        """
    if _dc_exec(create_project) != 0:
        fail("Magento source installation failed.")

    # ----------------------------------------------------------------------
    # >>> ADD THIS: ensure writable runtime dirs BEFORE setup:install
    # ----------------------------------------------------------------------
    perm_fix = r"""
        set -e
        cd /var/www/html
        mkdir -p var/cache var/page_cache var/di generated pub/static pub/media app/etc
        # Best-effort chown; on some bind mounts this may no-op (that's OK)
        chown -R www-data:www-data var generated pub/static pub/media app/etc || true
        # Directories: setgid + group write; Files: rw for owner/group
        find var generated pub/static pub/media app/etc -type d -exec chmod 2775 {} \;
        find var generated pub/static pub/media app/etc -type f -exec chmod 664 {} \;
        """
    _dc_exec(perm_fix)

    # 7) Install Magento
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
          --search-engine=elasticsearch8 \
          --elasticsearch-host=search --elasticsearch-port=9200
        """
    if _dc_exec(install) != 0:
        warn("Magento setup:install failed. Attempting to disable maintenance mode...")
        _dc_exec("php bin/magento maintenance:disable || true")
        fail("Magento setup:install failed. If database has old tables, re-run with --reset.")

    # 8) Optional sample data
    if with_sample:
        sample = r"""
        set -e
        cd /var/www/html
        bin/magento sampledata:deploy
        bin/magento setup:upgrade
        """
        if _dc_exec(sample) != 0:
            fail("Sample data deployment failed.")

    # (optional) Re-assert permissions for any new files after install/sample
    _dc_exec(perm_fix)

    # 9) Housekeeping
    _dc_exec(
        r"""
        set -e
        cd /var/www/html
        php bin/magento setup:static-content:deploy -f
        bin/magento cache:flush
        bin/magento indexer:reindex
        """

    )
    info(f"Done. Open: http://{site_host}:{app_port}/")
