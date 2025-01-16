# Деплой Telegram-бота на Timeweb Cloud

## Подготовка к деплою

### Необходимые переменные окружения

1. `BOT_TOKEN`: Токен вашего Telegram-бота от @BotFather
   - **ВАЖНО**: Никогда не публикуйте токен в открытом доступе!
   - Используйте секретные переменные в настройках Timeweb Cloud
   - Токен: `7875071911:AAFUbiivWfJr2E2Zhge4GCFWx5AacKzysmM`

2. `WEBHOOK_HOST`: Домен вашего приложения
   - Текущий домен: `txmerlxn-telegram-bot-v5-17ee.twc1.net`

3. `WEBHOOK_PORT`: Порт для webhook (по умолчанию 8080)

4. `USE_WEBHOOK`: Режим webhook (true/false)

### Безопасность токена

⚠️ **ПРЕДУПРЕЖДЕНИЕ**:
- Немедленно измените токен, если он был случайно опубликован
- Никогда не коммитьте токен в репозиторий
- Используйте переменные окружения для хранения чувствительных данных

### Настройка деплоя

#### Шаг 1: Подготовка Docker-образа
```bash
docker build -t telegram-bot .
```

#### Шаг 2: Настройки в Timeweb Cloud
1. Создайте новый проект
2. Выберите метод деплоя: Docker
3. Укажите следующие переменные окружения:
   - `BOT_TOKEN`: [ваш токен]
   - `WEBHOOK_HOST`: txmerlxn-telegram-bot-v5-17ee.twc1.net
   - `WEBHOOK_PORT`: 8080
   - `USE_WEBHOOK`: true

### Настройка Webhook для Telegram Bot

1. Полный URL webhook:
   ```
   https://txmerlxn-telegram-bot-v5-17ee.twc1.net/webhook
   ```

2. В настройках бота через @BotFather укажите этот webhook URL

### Проверка webhook

Для проверки webhook можно использовать команды:
```bash
# Установка webhook
curl -F "url=https://txmerlxn-telegram-bot-v5-17ee.twc1.net/webhook" \
     https://api.telegram.org/bot<ВАШ_ТОКЕН>/setWebhook

# Проверка текущего webhook
curl https://api.telegram.org/bot<ВАШ_ТОКЕН>/getWebhookInfo
```

## Возможные проблемы и решения

### Webhook не работает
- Проверьте корректность `BOT_TOKEN`
- Убедитесь, что порты открыты
- Проверьте логи приложения

### Ошибки при сборке Docker-образа
- Убедитесь, что все зависимости указаны в `requirements.txt`
- Проверьте, что `.dockerignore` настроен корректно

## Мониторинг и логирование

Используйте встроенные инструменты Timeweb Cloud для просмотра логов и состояния приложения.

## Обновление бота

При каждом обновлении:
1. Обновите код в репозитории
2. Пересоберите Docker-образ
3. Перезапустите приложение в Timeweb Cloud

---

*Последнее обновление: 17.01.2025*
