# docker/php/Dockerfile
# Purpose: PHP-FPM image for Magento/Mage-OS local dev with required extensions baked in.

FROM php:8.2-fpm

# Fail a layer if any command in a pipeline fails.
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# ------------------------------------------------------------
# OS deps for PHP extensions + basic tooling (git, unzip, curl, nc)
# ------------------------------------------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
    git unzip curl netcat-openbsd \
    libicu-dev libxml2-dev libzip-dev libxslt1-dev \
    libpng-dev libjpeg-dev libfreetype6-dev libonig-dev \
    libcurl4-openssl-dev pkg-config libssl-dev libsodium-dev \
 && rm -rf /var/lib/apt/lists/*

# ------------------------------------------------------------
# Build PHP extensions required by Magento (+ sockets, ftp)
# ------------------------------------------------------------
RUN docker-php-ext-configure gd --with-freetype --with-jpeg \
 && docker-php-ext-install -j"$(nproc)" \
    bcmath ctype curl dom gd intl mbstring opcache pdo_mysql \
    simplexml soap xsl zip sodium sockets ftp

# ------------------------------------------------------------
# Redis PHP extension (recommended for local dev)
# ------------------------------------------------------------
RUN pecl install redis \
 && docker-php-ext-enable redis

# ------------------------------------------------------------
# Composer (global)
# ------------------------------------------------------------
RUN curl -fsSL https://getcomposer.org/installer | php -- \
    --install-dir=/usr/local/bin --filename=composer

# Allow Composer to run as root inside the container
ENV COMPOSER_ALLOW_SUPERUSER=1

# ------------------------------------------------------------
# Pre-trust bind mount to avoid 'dubious ownership' (git)
# (also set at runtime in magento-setup for belt & suspenders)
# ------------------------------------------------------------
RUN git config --system safe.directory /var/www/html || true \
 && git config --global --add safe.directory /var/www/html || true

# ------------------------------------------------------------
# Dev-friendly PHP settings (tweak as needed)
# ------------------------------------------------------------
RUN { \
  echo 'memory_limit=2G'; \
  echo 'max_execution_time=1800'; \
  echo 'opcache.enable=1'; \
  echo 'opcache.enable_cli=1'; \
} > /usr/local/etc/php/conf.d/zz-magento.ini

# Workdir used by Nginx/PHP-FPM and your setup routines
WORKDIR /var/www/html

