# Официальный образ Python
FROM python:3.9

# Копирование исходного кода
COPY . /app

# Рабочая директория
WORKDIR /app

# Установка зависимостей
RUN pip install -r requirements.txt

# Команда запуска
ENTRYPOINT ["python"]

# Аргументы команды запуска
CMD ["bot_new.py"]

# Порт для webhook
EXPOSE 8080
