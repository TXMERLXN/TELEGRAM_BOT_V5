# Деплой Telegram бота на Timeweb Cloud

## Подготовка сервера

### 1. Аренда сервера
- Зайти на [Timeweb Cloud](https://timeweb.cloud)
- Выбрать тариф с Ubuntu
- Получить SSH-доступ

### 2. Первичная настройка
```bash
# Обновление системы
sudo apt update && sudo apt upgrade -y

# Установка Git
sudo apt install git -y
```

### 3. Запуск скрипта деплоя
```bash
# Скачать скрипт деплоя
wget https://raw.githubusercontent.com/TXMERLXN/TELEGRAM_BOT_V5/master/timeweb_deploy_script.sh

# Дать права на выполнение
chmod +x timeweb_deploy_script.sh

# Запустить скрипт
./timeweb_deploy_script.sh
```

## Управление ботом

### Основные команды
```bash
# Просмотр логов
docker-compose logs telegram-bot

# Перезапуск бота
docker-compose restart telegram-bot

# Остановка бота
docker-compose down
```

## Обновление бота
```bash
cd TELEGRAM_BOT_V5
git pull
docker-compose up -d --build
```

## Troubleshooting
- Проверьте логи: `docker-compose logs`
- Убедитесь, что порт 8080 открыт
- Проверьте корректность токена бота

**Внимание**: Храните токены в секрете!
