#!/bin/bash

# Делаем скрипт исполняемым
chmod +x "$0"

echo "Начинаем деплой в dev-окружение..."

# Проверяем, что мы находимся в ветке dev
CURRENT_BRANCH=$(git branch --show-current)
if [ "$CURRENT_BRANCH" != "dev" ]; then
	echo "Ошибка: Вы должны находиться в ветке dev для деплоя"
	exit 1
fi

# Проверяем наличие несохраненных изменений
if [ -n "$(git status --porcelain)" ]; then
	echo "Ошибка: Есть несохраненные изменения. Сделайте commit перед деплоем"
	exit 1
fi

# Проверяем наличие remote origin (GitHub)
if ! git remote | grep -q "origin"; then
	echo "Ошибка: Отсутствует remote 'origin'. Добавьте GitHub репозиторий"
	exit 1
fi

# Отправляем изменения в GitHub
echo "Отправляем изменения в GitHub..."
git push origin dev

# Переключаемся на master
echo "Переключаемся на master..."
git checkout master

# Мержим изменения из dev
echo "Мержим изменения из dev..."
git merge dev --no-ff -m "Merge dev branch for deployment"

# Отправляем изменения в GitHub master
echo "Отправляем изменения в GitHub master..."
git push origin master

# Возвращаемся в dev
git checkout dev

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

echo "Деплой успешно запущен!"