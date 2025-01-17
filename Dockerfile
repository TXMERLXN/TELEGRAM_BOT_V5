FROM python:3.9-slim

# Аргументы сборки
ARG BOT_TOKEN
ARG USE_WEBHOOK
ARG WEBHOOK_HOST
ARG WEBHOOK_PORT
ARG PYTHONUNBUFFERED
ARG RUNNINGHUB_API_KEY_1
ARG RUNNINGHUB_WORKFLOW_ID_1

# Рабочая директория
WORKDIR /app

# Копирование зависимостей
COPY requirements.txt .

# Установка зависимостей
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Копирование исходного кода
COPY . .

# Переменные окружения
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app \
    SENTRY_DSN=https://examplePublicKey@o0.ingest.sentry.io/0 \
    WEBHOOK_PORT=8443

# SSL диагностика и мониторинг
RUN python -c "from utils.ssl_check import check_ssl_certificate; print('SSL Check module imported successfully')"

# Создание директории для логов
RUN mkdir -p /app/logs

# Порт для webhook
EXPOSE 8443

# Команда запуска с gunicorn
CMD python -m utils.monitoring & \
    gunicorn \
    --workers 2 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:${WEBHOOK_PORT} \
    bot_new:app
