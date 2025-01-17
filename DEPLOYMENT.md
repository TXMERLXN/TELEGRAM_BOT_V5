# Развертывание Telegram Бота

## Требования
- Docker
- Docker Compose
- Доступ к Telegram Bot API
- SSL-сертификат

## Переменные окружения

Создайте файл `.env` со следующими переменными:

```env
# Telegram Bot
BOT_TOKEN=ваш_токен_бота
WEBHOOK_HOST=https://ваш_домен.com
WEBHOOK_PORT=8443

# RunningHub
RUNNINGHUB_API_KEY_1=ваш_api_ключ
RUNNINGHUB_WORKFLOW_ID_1=ваш_workflow_id

# Sentry (опционально)
SENTRY_DSN=ваш_sentry_dsn
```

## Деплой на Timeweb Cloud

1. Клонируйте репозиторий
```bash
git clone https://github.com/TXMERLXN/TELEGRAM_BOT_V5.git
cd TELEGRAM_BOT_V5
```

2. Настройте переменные окружения
```bash
cp .env.example .env
nano .env  # Отредактируйте файл
```

3. Соберите и запустите Docker-контейнер
```bash
docker-compose up --build -d
```

## Мониторинг

- Логи: `docker logs telegram-bot`
- Метрики: Sentry Dashboard
- Производительность: GitHub Actions Performance Report

## Безопасность

- Используйте надежный SSL-сертификат
- Регулярно обновляйте зависимости
- Контролируйте доступ к серверу

## Troubleshooting

1. Проверьте логи: `docker logs telegram-bot`
2. Убедитесь, что все переменные окружения установлены
3. Проверьте сетевые настройки и брандмауэр
