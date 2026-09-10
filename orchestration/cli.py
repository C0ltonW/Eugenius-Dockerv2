import argparse
import sys
from pathlib import Path
from .constants import PROFILES
from .env import ensure_env_file, load_env
from .utils import preflight
from .commands import do_generate, do_up, do_down, do_status, do_magento_setup

def main() -> None:
    """
    Parse CLI args, ensure .env, load env, run preflight, and dispatch command.
    Default with no args: 'up --profile full'.
    """
    parser = argparse.ArgumentParser(description="Profile-based Docker orchestrator for Magento dev")
    sub = parser.add_subparsers(dest="cmd")

    # For magento-setup
    p_setup = sub.add_parser("magento-setup", help="Install Mage-OS into ./src (idempotent)")
    p_setup.add_argument("--reset", action="store_true",
                         help="Uninstall first, then install (DROPS DB TABLES)")
    p_setup.add_argument("--with-sample-data", action="store_true",
                         help="Deploy sample data after install")
    p_setup.add_argument("--profile", choices=PROFILES.keys(), default="full",
                         help="Profile to start if the stack isn't already running (default: full)")

    p_gen = sub.add_parser("generate", help="Generate docker-compose.yaml (no up)")
    p_gen.add_argument("--profile", choices=PROFILES.keys(), default="full")

    p_up = sub.add_parser("up", help="Generate and start the stack")
    p_up.add_argument("--profile", choices=PROFILES.keys(), default="full")

    sub.add_parser("down", help="Stop and remove the stack (including volumes)")
    sub.add_parser("status", help="Show docker compose status")

    # Default: up --profile full
    if len(sys.argv) == 1:
        sys.argv += ["up", "--profile", "full"]

    args = parser.parse_args()

    env_path = Path(".env")
    ensure_env_file(env_path)
    env = load_env(env_path)

    # preflight guidance (WSL/Windows, vm.max_map_count)
    profile = getattr(args, "profile", "full")
    preflight(env, profile)

    if args.cmd == "generate":
        do_generate(args.profile, env)  # type: ignore[attr-defined]
    elif args.cmd == "up":
        do_up(args.profile, env)  # type: ignore[attr-defined]
    elif args.cmd == "down":
        do_down()
    elif args.cmd == "status":
        do_status()
    elif args.cmd == "magento-setup":
        do_magento_setup(env, reset=args.reset, with_sample=args.with_sample_data, profile=args.profile)
    else:
        parser.print_help()
