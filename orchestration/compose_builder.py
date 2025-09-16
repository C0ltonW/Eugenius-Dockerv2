from typing import Dict
from pathlib import Path
from .constants import PROFILES
from .nginx import ensure_nginx_conf, ensure_src_stub

def detect_search_flavor(search_image: str) -> str:
    """
    Return 'opensearch' or 'elasticsearch' based on image string.
    """
    img = (search_image or "").lower()
    if "elasticsearch" in img:
        return "elasticsearch"
    return "opensearch"

def resolve_search_jvm_opts(env: Dict[str, str], flavor: str) -> Dict[str, str]:
    """
    Map SEARCH_JAVA_OPTS or flavor-specific opts to the right env var.
    Priority:
      1) SEARCH_JAVA_OPTS
      2) ES_JAVA_OPTS / OPENSEARCH_JAVA_OPTS (other as fallback)
      3) '-Xms512m -Xmx512m'
    """
    generic = env.get("SEARCH_JAVA_OPTS")
    if flavor == "elasticsearch":
        specific = env.get("ES_JAVA_OPTS") or env.get("OPENSEARCH_JAVA_OPTS")
        value = (generic or specific or "-Xms512m -Xmx512m")
        return {"ES_JAVA_OPTS": value}
    else:
        specific = env.get("OPENSEARCH_JAVA_OPTS") or env.get("ES_JAVA_OPTS")
        value = (generic or specific or "-Xms512m -Xmx512m")
        return {"OPENSEARCH_JAVA_OPTS": value}

def build_compose(env: Dict[str, str], profile: str) -> Dict:
    """
    Build an in-memory Compose (v3.9) model for the selected profile.
    """
    if profile not in PROFILES:
        raise ValueError(f"Unknown profile '{profile}'. Available: {list(PROFILES.keys())}")

    services: Dict[str, Dict] = {}

    # candidate named volumes; we'll include only those actually referenced
    volume_candidates = {"dbdata": {}, "searchdata": {}, "rediscache": {}}

    # php (FPM)
    if "php" in PROFILES[profile]:
        services["php"] = {
            "image": env.get("PHP_IMAGE", "php:8.2-fpm"),
            "working_dir": "/var/www/html",
            "volumes": ["./src:/var/www/html"],
            "depends_on": [],
            "restart": "unless-stopped",
        }
        # Auto-build local PHP image if Dockerfile is present.
        if Path("./docker/php/Dockerfile").exists():
            services["php"]["build"] = {"context": "./docker/php"}

    # db
    if "db" in PROFILES[profile]:
        services["db"] = {
            "image": env.get("DB_IMAGE", "mariadb:10.6"),
            "command": "--log-bin-trust-function-creators=1",
            "environment": {
                "MYSQL_ROOT_PASSWORD": env.get("MYSQL_ROOT_PASSWORD", "root"),
                "MYSQL_DATABASE": env.get("MYSQL_DATABASE", "magento"),
                "MYSQL_USER": env.get("MYSQL_USER", "magento"),
                "MYSQL_PASSWORD": env.get("MYSQL_PASSWORD", "magento"),
            },
            "volumes": ["dbdata:/var/lib/mysql"],
            "ports": [f"{env.get('DB_PORT', '3316')}:3306"],
            "restart": "unless-stopped",
        }
        if "php" in services:
            services["php"]["depends_on"].append("db")

    # search (OpenSearch or Elasticsearch)
    if "search" in PROFILES[profile]:
        search_image = env.get("SEARCH_IMAGE", "opensearchproject/opensearch:2.11.0")
        flavor = detect_search_flavor(search_image)

        search_env = {"discovery.type": "single-node"}
        search_env.update(resolve_search_jvm_opts(env, flavor))

        svc: Dict = {
            "image": search_image,
            "environment": search_env,
            "volumes": ["searchdata:/usr/share/opensearch/data"] if flavor == "opensearch" else [],
            "ports": [f"{env.get('SEARCH_PORT', '9201')}:9200"],
            "restart": "unless-stopped",
        }

        if flavor == "opensearch":
            svc["ulimits"] = {"memlock": {"soft": -1, "hard": -1}}
        else:
            # Disable Elasticsearch 8 security in dev for convenience (not for prod)
            svc["environment"]["xpack.security.enabled"] = "false"

        services["search"] = svc
        if "php" in services:
            services["php"]["depends_on"].append("search")

    # nginx (full)
    if "nginx" in PROFILES[profile]:
        ensure_nginx_conf()
        ensure_src_stub()
        services["nginx"] = {
            "image": env.get("NGINX_IMAGE", "nginx:alpine"),
            "ports": [f"{env.get('APP_PORT', '81')}:80"],
            "volumes": [
                "./src:/var/www/html:ro",
                "./nginx/conf.d/default.conf:/etc/nginx/conf.d/default.conf:ro",
            ],
            "depends_on": ["php"],
            "restart": "unless-stopped",
        }

    # redis (optional)
    if "redis" in PROFILES[profile]:
        services["redis"] = {
            "image": env.get("REDIS_IMAGE", "redis:alpine"),
            "volumes": ["rediscache:/data"],
            "ports": [f"{env.get('REDIS_PORT', '6381')}:6379"],
            "restart": "unless-stopped",
        }
        if "php" in services:
            services["php"]["depends_on"].append("redis")

    # prune unused volumes
    used_volume_names = set()
    for svc in services.values():
        for mount in (svc.get("volumes", []) or []):
            if isinstance(mount, str) and ":" in mount and not mount.startswith("."):
                vol_name = mount.split(":", 1)[0]
                used_volume_names.add(vol_name)

    volumes = {name: volume_candidates[name] for name in used_volume_names if name in volume_candidates}

    compose = {
        "name": env.get("COMPOSE_PROJECT_NAME", "magedev"),
        "services": services,
        "volumes": volumes,
    }
    return compose
