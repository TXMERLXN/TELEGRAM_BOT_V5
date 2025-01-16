# Официальный образ Python
FROM python:3.9

# Установка системных зависимостей
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
ENV PYTHONUNBUFFERED=1

# Порт для webhook
EXPOSE 8080

# Команда запуска с gunicorn
CMD ["gunicorn", "-b", "0.0.0.0:8080", "-w", "2", "bot_new:main", "--log-level", "debug"]
