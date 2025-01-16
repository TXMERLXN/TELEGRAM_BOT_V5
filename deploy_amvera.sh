#!/bin/bash

# Обновление зависимостей
pip install -r requirements.txt

# Настройка переменных окружения для dev
export BOT_TOKEN=7875071911:AAFUbiivWfJr2E2Zhge4GCFWx5AacKzysmM
export WEBHOOK_HOST=bot-v5-dev.amvera.io
export WEBHOOK_PORT=8080
export USE_WEBHOOK=true

# Запуск миграций (если необходимо)
# python manage.py migrate

# Запуск бота
python bot_new.py
