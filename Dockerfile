# Используем официальный образ Python
FROM python:3.9-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем файлы проекта
COPY . /app

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Устанавливаем переменные окружения
ENV BOT_TOKEN=7875071911:AAFUbiivWfJr2E2Zhge4GCFWx5AacKzysmM
ENV WEBHOOK_HOST=bot-v5-timeweb.cloud
ENV WEBHOOK_PORT=8080
ENV USE_WEBHOOK=true

# Открываем порт
EXPOSE 8080

# Команда запуска
CMD ["python", "bot_new.py"]
