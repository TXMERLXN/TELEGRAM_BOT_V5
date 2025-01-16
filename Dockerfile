# Официальный образ Python
FROM python:3.9-slim

# Метаданные
LABEL maintainer="TXMERLXN <txmerlxn@example.com>"
LABEL description="Telegram Bot for AI Product Photo Generation"

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Создание пользователя для безопасности
RUN useradd -m appuser
USER appuser

# Рабочая директория
WORKDIR /home/appuser/app

# Копирование зависимостей
COPY --chown=appuser:appuser requirements.txt .

# Установка зависимостей
RUN pip install --no-cache-dir -r requirements.txt

# Копирование исходного кода
COPY --chown=appuser:appuser . .

# Переменные окружения
ENV BOT_TOKEN=${BOT_TOKEN}
ENV WEBHOOK_HOST=${WEBHOOK_HOST}
ENV WEBHOOK_PORT=${WEBHOOK_PORT:-8080}
ENV USE_WEBHOOK=true
ENV PYTHONUNBUFFERED=1

# Порт для webhook
EXPOSE 8080

# Команда запуска
CMD ["gunicorn", "-b", "0.0.0.0:8080", "-w", "2", "-k", "uvicorn.workers.UvicornWorker", "bot_new:main", "--log-level", "warning"]
