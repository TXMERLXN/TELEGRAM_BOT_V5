# Официальный образ Python
FROM python:3.9-slim

# Метаданные
LABEL maintainer="TXMERLXN <txmerlxn@example.com>"
LABEL description="Telegram Bot for AI Product Photo Generation"

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

# Порт для webhook
EXPOSE 8080

# Команда запуска
CMD ["python", "bot_new.py"]
