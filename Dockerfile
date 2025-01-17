FROM python:3.9-slim

# Базовый Dockerfile для деплоя
WORKDIR /app

# Копирование зависимостей
COPY requirements.txt .

# Установка зависимостей
RUN pip install --no-cache-dir -r requirements.txt

# Копирование проекта
COPY . .

# Установка переменных окружения
ENV PYTHONUNBUFFERED=1

# Точка входа
CMD ["python", "bot_new.py"]
