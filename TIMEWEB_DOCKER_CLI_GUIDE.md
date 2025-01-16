# Использование Timeweb CLI через Docker

## Предварительная настройка

### 1. Установка Docker Desktop
- Скачайте и установите [Docker Desktop](https://www.docker.com/products/docker-desktop)
- Перезагрузите компьютер

### 2. Загрузка образа Timeweb CLI
```bash
docker pull timeweb/cli
```

## Использование CLI

### Базовые команды
```bash
# Авторизация
docker run -it --rm timeweb/cli login

# Список серверов
docker run -it --rm timeweb/cli server list

# Создание сервера
docker run -it --rm timeweb/cli server create \
    --name telegram-bot \
    --os ubuntu-22.04
```

### Удобный скрипт timeweb_docker_cli.bat
```bash
# Авторизация
timeweb_docker_cli.bat login

# Список серверов
timeweb_docker_cli.bat server list
```

## Постоянное хранение конфигурации
- Монтируйте том `/root/.twc` для сохранения авторизации
- Используйте `-v %USERPROFILE%/.twc:/root/.twc`

## Безопасность
- Не храните sensitive-данные в открытом виде
- Используйте переменные окружения
- Очищайте историю команд

## Troubleshooting
- Обновляйте Docker Desktop
- Проверяйте версию CLI
- Используйте `--help` для справки

**Внимание**: Всегда проверяйте команды перед выполнением!
