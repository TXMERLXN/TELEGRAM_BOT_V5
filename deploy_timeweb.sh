#!/bin/bash

# Обновление зависимостей
pip install -r requirements.txt

# Сборка и запуск Docker-контейнера
docker-compose down
docker-compose build
docker-compose up -d

# Проверка статуса контейнера
docker-compose ps
docker-compose logs telegram-bot
