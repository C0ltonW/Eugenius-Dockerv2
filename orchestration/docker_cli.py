import subprocess
from typing import List
from .utils import info

def docker_compose_cmd(args: List[str]) -> int:
    """
    Execute a docker compose CLI command in the current working directory.
    """
    cmd = ["docker", "compose"] + args
    info(" ".join(cmd))
    return subprocess.call(cmd)
