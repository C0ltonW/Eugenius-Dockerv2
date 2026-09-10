from textwrap import dedent
from typing import Dict, Tuple

DEFAULT_ENV = dedent("""\
# -------- Project prefix / naming --------
# Compose project name (prefixes containers & network)
COMPOSE_PROJECT_NAME=magedev

# -------- Host & ports --------
# Where you'll reach the site (Profiles containing 'app' container)
SITE_HOST=127.0.0.1
APP_PORT=81

# Expose service ports to host (helpful for tooling/inspection)
DB_PORT=3316
SEARCH_PORT=9201
REDIS_PORT=6381

# -------- Images (override with your own custom images if desired) --------
# PHP image (must include Magento-required extensions if custom)
PHP_IMAGE=php:8.2-fpm
# Database image (switch by commenting/uncommenting)
# DB_IMAGE=mariadb:10.6
DB_IMAGE=mysql:8.0

# Search engine image (switch by commenting/uncommenting)
# SEARCH_IMAGE=opensearchproject/opensearch:2.11.0
SEARCH_IMAGE=docker.elastic.co/elasticsearch/elasticsearch:8.15.0

# Web server image
NGINX_IMAGE=nginx:alpine

# Cache image
REDIS_IMAGE=redis:alpine

# -------- Database credentials --------
MYSQL_ROOT_PASSWORD=root
MYSQL_DATABASE=magento
MYSQL_USER=magento
MYSQL_PASSWORD=magento

# -------- Search JVM heap (tune as needed) --------
# Preferred generic knob for either OpenSearch or Elasticsearch (mapped appropriately).
SEARCH_JAVA_OPTS=-Xms512m -Xmx512m
# Back-compat/fine-grain knobs (optional; SEARCH_JAVA_OPTS takes precedence if set):
# OPENSEARCH_JAVA_OPTS=-Xms512m -Xmx512m
# ES_JAVA_OPTS=-Xms512m -Xmx512m
""")

DEFAULT_NGINX_CONF = dedent("""\
server {
  listen 80;
  server_name _;
  root /var/www/html/pub;
  index index.php index.html;

  # Basic security headers (dev-friendly)
  add_header X-Content-Type-Options nosniff;
  add_header X-Frame-Options SAMEORIGIN;

  # Let Magento front controller handle non-existent files
  location / {
    try_files $uri $uri/ /index.php$is_args$args;
  }

  # Static assets
  location ~* \\.(jpg|jpeg|png|gif|css|js|ico|svg|webp|avif)$ {
    try_files $uri =404;
    expires 1h;
    access_log off;
  }

  # Media and static handlers (Magento conventions)
  location /media/ {
    try_files $uri $uri/ /get.php?$args;
  }
  location /static/ {
    try_files $uri $uri/ /static.php?resource=$uri&$args;
  }

  # PHP-FPM
  location ~ \\.php$ {
    try_files $uri =404;
    include fastcgi_params;
    fastcgi_param SCRIPT_FILENAME $realpath_root$fastcgi_script_name;
    fastcgi_param DOCUMENT_ROOT $realpath_root;
    fastcgi_pass php:9000;
    fastcgi_index index.php;
    # Helpful dev overrides (adjust as needed)
    fastcgi_param PHP_VALUE "memory_limit=2G\nmax_execution_time=1800\nupload_max_filesize=64M\npost_max_size=64M";
  }

  # Deny access to sensitive files
  location ~* (\\.git|\\.env|composer\\.(json|lock)|auth\\.json|package\\.json|phpunit\\.xml) {
    deny all;
  }
}
""")

PROFILES: Dict[str, Tuple[str, ...]] = {
    "minimal": ("php", "db", "search"),
    "test": ["php", "db", "search", "nginx"],
    "full": ("php", "db", "search", "nginx", "redis"),
}
