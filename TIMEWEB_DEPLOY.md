# Деплой Telegram бота на Timeweb Cloud

## Подготовка окружения

### 1. Установка Docker
```bash
sudo apt update
sudo apt install docker.io docker-compose
sudo usermod -aG docker $USER
```

### 2. Клонирование репозитория
```bash
git clone https://github.com/TXMERLXN/TELEGRAM_BOT_V5.git
cd TELEGRAM_BOT_V5
```

### 3. Настройка переменных окружения
- Отредактируйте `.env` файл с токеном бота
- Настройте webhook-хост

### 4. Сборка и запуск
```bash
chmod +x deploy_timeweb.sh
./deploy_timeweb.sh
```

### 5. Мониторинг
```bash
docker-compose logs telegram-bot
docker-compose ps
```

## Troubleshooting
- Проверьте открытые порты
- Убедитесь, что Docker запущен
- Проверьте логи контейнера

## Обновление
```bash
git pull
./deploy_timeweb.sh
```
