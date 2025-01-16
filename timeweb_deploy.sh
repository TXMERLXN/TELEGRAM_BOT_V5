#!/bin/bash

# Деплой на Timeweb Cloud
echo "Начало деплоя на Timeweb Cloud"

# Сборка Docker-образа
docker build -t telegram-bot .

# Загрузка образа в репозиторий Timeweb
docker tag telegram-bot registry.timeweb.cloud/telegram-bot
docker push registry.timeweb.cloud/telegram-bot

# Деплой с использованием docker-compose
docker-compose -f timeweb_deploy.yml up -d

echo "Деплой завершен"
