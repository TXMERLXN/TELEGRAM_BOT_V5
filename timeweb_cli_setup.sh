#!/bin/bash

# Установка Timeweb CLI

# Обновление системы
sudo apt update && sudo apt upgrade -y

# Установка зависимостей
sudo apt install -y curl gpg

# Добавление GPG-ключа
curl -fsSL https://repo.timeweb.cloud/gpg | sudo gpg --dearmor -o /usr/share/keyrings/timeweb-archive-keyring.gpg

# Добавление репозитория
echo "deb [signed-by=/usr/share/keyrings/timeweb-archive-keyring.gpg] https://repo.timeweb.cloud/debian stable main" | sudo tee /etc/apt/sources.list.d/timeweb.list

# Обновление списка пакетов
sudo apt update

# Установка Timeweb CLI
sudo apt install -y twc-cli

# Авторизация
twc login

# Проверка версии
twc version

# Список доступных команд
twc help

# Создание конфигурационного файла
mkdir -p ~/.config/timeweb
touch ~/.config/timeweb/config.yaml

# Базовая конфигурация
cat > ~/.config/timeweb/config.yaml << EOL
# Конфигурация Timeweb CLI
default_output: table
log_level: info
EOL

echo "Timeweb CLI установлен и настроен"
