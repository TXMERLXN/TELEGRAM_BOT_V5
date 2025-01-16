# Официальный образ Python
FROM python:3.9-slim

# Метаданные
LABEL maintainer="TXMERLXN <txmerlxn@example.com>"
LABEL description="Telegram Bot for AI Product Photo Generation"

# Обновление системных пакетов
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Рабочая директория
WORKDIR /app

# Копирование зависимостей
COPY requirements.txt .

# Установка зависимостей
RUN pip install --no-cache-dir -r requirements.txt

# Копирование исходного кода
COPY . .

# Переменные окружения
ENV BOT_TOKEN=${BOT_TOKEN}
ENV WEBHOOK_HOST=${WEBHOOK_HOST}
ENV WEBHOOK_PORT=${WEBHOOK_PORT:-8080}
ENV USE_WEBHOOK=true
ENV PYTHONUNBUFFERED=1

# Порт для webhook (соответствует требованиям Timeweb Cloud)
EXPOSE 8080

# Команда запуска с gunicorn
CMD ["gunicorn", "-b", "0.0.0.0:8080", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "bot_new:main"]
