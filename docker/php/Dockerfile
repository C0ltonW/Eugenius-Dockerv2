FROM php:8.2-fpm

# OS deps for PHP extensions + tools used by your scripts (curl, nc)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git unzip curl netcat-openbsd \
    libicu-dev libxml2-dev libzip-dev libxslt1-dev \
    libpng-dev libjpeg-dev libfreetype6-dev libonig-dev \
    libcurl4-openssl-dev pkg-config libssl-dev libsodium-dev \
 && rm -rf /var/lib/apt/lists/*

# gd config + core Magento extensions (+ sockets, ftp)
RUN docker-php-ext-configure gd --with-freetype --with-jpeg \
 && docker-php-ext-install -j$(nproc) \
    bcmath ctype curl dom gd intl mbstring opcache pdo_mysql \
    simplexml soap xsl zip sodium sockets ftp

# Redis PHP extension (optional but recommended)
RUN pecl install redis \
 && docker-php-ext-enable redis

# Composer (global)
RUN curl -fsSL https://getcomposer.org/installer | php -- \
    --install-dir=/usr/local/bin --filename=composer

# Let Composer run as root (container) to avoid warnings
ENV COMPOSER_ALLOW_SUPERUSER=1

# (Optional) Pre-trust the working directory to avoid 'dubious ownership' on bind mounts.
# This is safe and just writes config; it's also handled in your setup script now,
# but keeping it here makes the image friendlier for ad-hoc usage too.
RUN git config --system safe.directory /var/www/html || true \
 && git config --global --add safe.directory /var/www/html || true

# Dev-friendly PHP settings
RUN { \
  echo 'memory_limit=2G'; \
  echo 'max_execution_time=1800'; \
  echo 'opcache.enable=1'; \
  echo 'opcache.enable_cli=1'; \
} > /usr/local/etc/php/conf.d/zz-magento.ini

WORKDIR /var/www/html
