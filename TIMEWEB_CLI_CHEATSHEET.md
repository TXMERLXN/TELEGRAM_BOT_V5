# Timeweb CLI - Шпаргалка

## Установка и настройка
```bash
# Установка
sudo apt install twc-cli

# Авторизация
twc login
```

## Управление серверами
```bash
# Список серверов
twc server list

# Создание сервера
twc server create \
  --name telegram-bot \
  --os ubuntu-22.04 \
  --cpu 2 \
  --ram 4 \
  --disk 50

# Получение информации о сервере
twc server get <server_id>

# Запуск/остановка сервера
twc server start <server_id>
twc server stop <server_id>
```

## Работа с SSH
```bash
# Добавление SSH-ключа
twc ssh-key add --name bot-server-key --public-key ~/.ssh/id_rsa.pub

# Список SSH-ключей
twc ssh-key list
```

## Сетевые настройки
```bash
# Настройка файервола
twc firewall create \
  --name bot-firewall \
  --rules '{"inbound": [{"port": 8080, "protocol": "tcp"}]}'
```

## Мониторинг и логи
```bash
# Просмотр логов сервера
twc server logs <server_id>

# Мониторинг ресурсов
twc server stats <server_id>
```

## Деплой приложений
```bash
# Деплой через Git
twc app deploy \
  --name telegram-bot \
  --repository https://github.com/TXMERLXN/TELEGRAM_BOT_V5.git \
  --branch master
```

## Конфигурация
```bash
# Настройка профиля
twc config set default_output=json
twc config set log_level=debug
```

## Безопасность
```bash
# Управление токенами
twc token list
twc token revoke <token_id>
```

## Полезные команды
```bash
# Версия CLI
twc version

# Справка
twc help
twc help server
```

## Примечания
- Всегда проверяйте команды перед выполнением
- Используйте осторожно команды изменения/удаления
- Храните токены в безопасности
