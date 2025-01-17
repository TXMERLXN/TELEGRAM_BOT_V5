FROM python:3.9-slim

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
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Порт для webhook
EXPOSE 8080

# Команда запуска с gunicorn
CMD ["gunicorn", "-b", "0.0.0.0:8080", "-w", "2", "bot_new:main", "--log-level", "debug"]
