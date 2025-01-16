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
ENV BOT_TOKEN=7875071911:AAFUbiivWfJr2E2Zhge4GCFWx5AacKzysmM
ENV WEBHOOK_HOST=bot-v5.timeweb.cloud
ENV WEBHOOK_PORT=8080
ENV USE_WEBHOOK=true

# Порт для webhook
EXPOSE 8080

# Команда запуска
CMD ["python", "bot_new.py"]
