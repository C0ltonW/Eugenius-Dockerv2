# Eugenius-Docker v2 — Magento Development Stack

A lightweight, profile-driven Docker orchestration system for **Magento / Mage-OS development**.  
This stack is designed to be simple, modular, and beginner-friendly — while still allowing advanced customization.  

It provisions a full Magento development environment with **PHP-FPM, MySQL/MariaDB, Elasticsearch/OpenSearch, optional Redis, and Nginx**.

>Note: This repo favors step‑by‑step UX and copy‑pasteable commands. If you’re new to Docker, follow the Runbooks below first.
---

## Features
- **Profiles** to choose between lightweight or full stacks (`minimal`, `test`, `full`).
- **One-command Magento install** (with sample data optional).
- **Automatic config generation** (`.env` and `nginx/default.conf`) on first run.
- **Beginner-friendly defaults** — works out of the box.
- **Search flexibility** — switch between Elasticsearch and OpenSearch.
- **Portable** — works in Windows PowerShell, WSL2, or Linux/Mac.

---

## Requirements
- [Docker Desktop](https://docs.docker.com/desktop/) (with **WSL2 backend** enabled on Windows).
- Docker Compose v2 (ships with Docker Desktop).
- Python `3.10+` (tested with `3.12`).
- Pip (`pip install pyyaml`).
>Tip: Keep the project inside your WSL Linux filesystem (e.g., ~/projects/...) for fast bind‑mounts and reliable file‑watching. The tool will warn you if you run it from a Windows path.
---

## Quick Start

### 0. Bootstrapping (If needed) 
    #!/bin/bash

    # Update package list and install required tools: Git, Docker, Python 3.12, pip, and Docker Compose v2
    sudo apt update
    sudo apt install -y git docker.io python3.12 python3-pip docker-compose-v2
    
    # Start Docker service
    sudo service docker start
    
    # Add user to Docker group to avoid needing sudo for Docker commands
    sudo usermod -aG docker $USER
    
    # Set vm.max_map_count for Elasticsearch/OpenSearch compatibility
    sudo sysctl -w vm.max_map_count=262144
    
    # Create a projects directory in the WSL filesystem for performance
    mkdir -p ~/projects
    cd ~/projects
    
    # Install Python dependency pyyaml
    pip3 install pyyaml


### 1. Clone the repo
    git clone https://github.com/C0ltonW/Eugenius-Dockerv2.git my-magento
    cd my-magento

### 2. (Optional) Create a virtual environment
> You likely won't need this. This is for setups that explicitly need one.

    python -m venv .venv
    source .venv/bin/activate   # Linux/WSL
    .venv\Scripts\activate      # PowerShell

### 3. Install dependencies
    pip install pyyaml

### 4. Start the stack (default: full profile)
> Note: Running python orchestrator.py with no args is equivalent to `up --profile full`.

    python orchestrator.py
    # or
    python orchestrator.py up --profile full




### 5. Access your site
👉 http://127.0.0.1:81/

---

## Profiles

| Profile   | Services                          |
|-----------|----------------------------------|
| `minimal` | PHP, Database, Search             |
| `test`    | PHP, Database, Search, Nginx      |
| `full`    | PHP, Database, Search, Nginx, Redis |

---

## Environment Variables (`.env`)

Your `.env` controls host ports, images, and credentials. It is auto-generated on first run.  

| Variable             | Purpose |
|----------------------|---------|
| `COMPOSE_PROJECT_NAME` | Prefix for containers, networks, volumes |
| `SITE_HOST`            | Hostname/IP for Nginx (default `127.0.0.1`) |
| `APP_PORT`             | Host port mapped to Nginx (`81 → 80`) |
| `DB_PORT`              | MySQL/MariaDB port (`3316 → 3306`) |
| `SEARCH_PORT`          | Search port (`9201 → 9200`) |
| `REDIS_PORT`           | Redis port (`6381 → 6379`) |
| `PHP_IMAGE`            | PHP-FPM image |
| `DB_IMAGE`             | DB engine (`mysql:8.0` or `mariadb:10.6`) |
| `SEARCH_IMAGE`         | Search engine (`opensearch` or `elasticsearch`) |
| `MYSQL_*`              | DB credentials (`root`, `user`, `password`) |
| `SEARCH_JAVA_OPTS`     | JVM heap tuning for search engines |

🔄 Switching search engines:
    # Elasticsearch
    SEARCH_IMAGE=docker.elastic.co/elasticsearch/elasticsearch:8.15.0

    # OpenSearch
    SEARCH_IMAGE=opensearchproject/opensearch:2.11.0

---

## ️CLI Commands

    python orchestrator.py <command> [flags]

| Command         | Flags                                                           | Description |
|-----------------|----------------------------------------------------------------|-------------|
| `up`            | `--profile {minimal, full, test}` (default: `full`)            | Generate and start containers |
| `down`          | *(none)*                                                       | Stop and remove stack + volumes |
| `status`        | *(none)*                                                       | Show container status |
| `generate`      | `--profile {minimal, full, test}`                              | Generate `docker-compose.yaml` only |
| `magento-setup` | `--reset`, `--with-sample-data`                                | Install Magento/Mage-OS into `./src` |

---

## Magento Installation Guide

### 1. Basic install
    python orchestrator.py magento-setup

This will:
- Start the **full stack**
- Clone Mage-OS into `./src`
- Run Composer install
- Install Magento with `.env` defaults

### 2. With sample data
    python orchestrator.py magento-setup --with-sample-data

### 3. Reinstall/reset
    python orchestrator.py magento-setup --reset

---

## Importing Your Own Database

### Import into an empty database
If your `.env` defines an empty `magento` schema (first run or after `--reset`):
    docker compose exec -T db mysql -u magento -pmagento magento < db_dump.sql

### Import into an existing database (tables already populated)
If tables already exist in the `magento` schema, you have two options:

1. **Overwrite existing tables (not always safe, but fast):**
    docker compose exec -T db mysql -u magento -pmagento --force magento < db_dump.sql

   - The `--force` flag tells MySQL to continue even if tables already exist.  
   - Existing rows may remain if not overwritten by the dump.  

2. **Clean reinstall (recommended for consistency):**
    python orchestrator.py magento-setup --reset
    docker compose exec -T db mysql -u magento -pmagento magento < db_dump.sql

   - This drops Magento, clears all tables, and ensures the DB matches your dump.  

>⚠️ Note: If your dump includes Magento’s own schema, use `--reset` first to avoid version mismatch errors. 
> The DB container starts with `--log-bin-trust-function-creators=1` to ease imports that create functions/triggers.



---

## Common Docker Commands

| Command                                                   | Description                                     |
|-----------------------------------------------------------|-------------------------------------------------|
| `docker compose ps`                                       | Show running containers                         |
| `docker compose logs -f`                                  | Follow logs                                     |
| `docker compose logs -f <service>`                        | Follow specific container log                   |
| `docker compose exec php bash`                            | Shell inside PHP                                |
| `docker compose build php && docker compose up -d php`    | One line rebuild after editing Dockerfile       |
| `docker compose exec db mysql -umagento -pmagento magento` | DB shell                                        |
| `docker system prune -f`                                  | Cleanup stopped containers/images (Be careful!) |
| `docker compose config`                                    | Inspect effect compose config                   |

---

Runbook
=======

### Clone the repo into a dir
```
git clone https://github.com/C0ltonW/Eugenius-Dockerv2.git my-magento
```

### Change directories into the newly created `/my-magento/`
```
cd my-magento
```
### Create Virtual Environment (Optional)
```
python -m venv .venv
.venv\Scripts\activate
```
### Install pyyaml
```
pip install pyyaml
```
### Start the container stack
```
python orchestrator.py up --profile full
```
### Install magento with sample data
```
python orchestrator.py magento-setup --with-sample-data
```

---

## Custom Profiles

Defined in `orchestration/constants.py`

    PROFILES = {
        "minimal": ("php", "db", "search"),
        "full": ("php", "db", "search", "nginx", "redis"),
    }

Run with:
    `python orchestrator.py up --profile <profile>`

---

## Troubleshooting

**Site unreachable**
  - Check `APP_PORT` in `.env`.
  - Ensure `nginx/conf.d/default.conf` exists.
  - Confirm `fastcgi_pass php:9000;` in the Nginx config.
  - Logs: `docker compose logs -f nginx php`.

**Search engine fails**
  - On Windows/WSL2 set `vm.max_map_count=262144`.
  - Lower JVM heap in `.env`, e.g. `SEARCH_JAVA_OPTS=-Xms512m -Xmx512m`.
  - Logs: `docker compose logs -f search`.

**Port already in use**
  - Change `APP_PORT`, `DB_PORT`, `SEARCH_PORT`, `REDIS_PORT` in `.env`, then `up` again.

**Very slow file I/O on Windows**
  - Move the project into your **WSL filesystem** (not `/mnt/c/...`).

**Composer/Git safe directory warnings**
  - The PHP image pre‑adds `/var/www/html` as a safe Git directory and installs Composer globally. Rebuild if you changed the Dockerfile.

**`magento-setup` says DB/Search not reachable**
  - It retries ~3 minutes. Check `docker compose logs -f db search`.

**DB import errors**
- Use `--reset`
- Or import with `--force`

---

## 📂 Project Structure
```
.
├── orchestrator.py
├── orchestration/
│   ├── cli.py
│   ├── commands.py
│   ├── compose_builder.py
│   ├── constants.py
│   ├── env.py
│   ├── nginx.py
│   └── utils.py
├── docker/php/Dockerfile
├── templates/
│   ├── env.default
│   └── nginx/default.conf
├── nginx/conf.d/
└── src/
```
---

## How It Works
1. Python builds `docker-compose.yaml` from profiles + `.env`
2. Auto-generates configs if missing
3. Docker Compose runs services
4. `magento-setup` installs Magento, optional sample data
5. `./src` bind-mounted into containers

---



