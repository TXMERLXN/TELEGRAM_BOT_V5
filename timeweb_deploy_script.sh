#!/bin/bash

# Обновление системы
sudo apt update && sudo apt upgrade -y

# Установка необходимых утилит
sudo apt install -y git curl wget software-properties-common

# Установка Docker
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose

# Добавление текущего пользователя в группу docker
sudo usermod -aG docker $USER

# Клонирование репозитория
git clone https://github.com/TXMERLXN/TELEGRAM_BOT_V5.git
cd TELEGRAM_BOT_V5

# Создание .env файла с переменными
cat > .env << EOL
BOT_TOKEN=7875071911:AAFUbiivWfJr2E2Zhge4GCFWx5AacKzysmM
WEBHOOK_HOST=bot-v5.timeweb.cloud
WEBHOOK_PORT=8080
USE_WEBHOOK=true
EOL

# Сборка и запуск Docker-контейнера
docker-compose up -d --build

# Проверка статуса контейнера
docker-compose ps
docker-compose logs telegram-bot

# Настройка файервола
sudo ufw allow 8080/tcp

echo "Деплой завершен. Бот запущен."
