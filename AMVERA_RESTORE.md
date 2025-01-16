# Восстановление репозитория на Amvera

## Шаги восстановления

### 1. Вход в личный кабинет
- Перейти на [https://amvera.ru](https://amvera.ru)
- Войти под учетной записью `txmerlxn`

### 2. Создание нового проекта
- Нажать "Создать проект"
- Выбрать тип: "Python"
- Название проекта: `telegram-bot-v5-dev`

### 3. Настройка источника кода
- Источник: Git
- URL репозитория: `https://github.com/TXMERLXN/TELEGRAM_BOT_V5.git`
- Ветка: `master`

### 4. Конфигурация проекта
- Версия Python: 3.9
- Путь к requirements: `requirements.txt`
- Команда запуска: `bash deploy_amvera.sh`

### 5. Переменные окружения
- `BOT_TOKEN`: 7875071911:AAFUbiivWfJr2E2Zhge4GCFWx5AacKzysmM
- `WEBHOOK_HOST`: bot-v5-dev.amvera.io
- `WEBHOOK_PORT`: 8080
- `USE_WEBHOOK`: true

### Возможные проблемы
- Проверить права доступа к GitHub-репозиторию
- Убедиться, что SSH-ключи корректны
- Проверить наличие файла `amvera.yml`

## Команды для проверки
```bash
# Проверка SSH-соединения
ssh -T git@github.com

# Проверка URL репозитория
git remote -v
```

**Внимание**: При возникновении проблем обратиться в поддержку Amvera
