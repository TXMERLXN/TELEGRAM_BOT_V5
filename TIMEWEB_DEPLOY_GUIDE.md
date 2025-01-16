# Руководство по деплою на Timeweb Cloud

## Подготовка окружения

### 1. Регистрация и настройка
- Зарегистрироваться на [Timeweb Cloud](https://timeweb.cloud)
- Создать виртуальный сервер с Ubuntu
- Настроить SSH-доступ

### 2. Установка Docker
```bash
# Обновление системы
sudo apt update && sudo apt upgrade -y

# Установка Docker
sudo apt install docker.io docker-compose -y

# Добавление текущего пользователя в группу docker
sudo usermod -aG docker $USER
```

### 3. Клонирование репозитория
```bash
git clone https://github.com/TXMERLXN/TELEGRAM_BOT_V5.git
cd TELEGRAM_BOT_V5
```

### 4. Настройка переменных
- Отредактируйте `.env` или передайте переменные в `docker-compose.yml`
- Укажите актуальный `BOT_TOKEN`
- Настройте `WEBHOOK_HOST`

### 5. Сборка и запуск
```bash
# Сборка образа
docker-compose build

# Запуск контейнера
docker-compose up -d

# Проверка статуса
docker-compose ps
docker-compose logs telegram-bot
```

### 6. Настройка файервола
```bash
# Открытие порта 8080
sudo ufw allow 8080/tcp
```

## Обновление бота
```bash
git pull
docker-compose down
docker-compose build
docker-compose up -d
```

## Мониторинг
```bash
# Просмотр логов
docker-compose logs -f telegram-bot

# Проверка использования ресурсов
docker stats
```

## Возможные проблемы
- Проверьте корректность токена
- Убедитесь, что порт 8080 открыт
- Проверьте наличие Docker и docker-compose

**Внимание**: Всегда храните токены в секрете!
