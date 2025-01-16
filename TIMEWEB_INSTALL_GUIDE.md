# Установка Timeweb CLI в Windows

## Способ 1: Установка через Docker

### Предварительные требования
- Установленный Docker Desktop
- Активная учетная запись Timeweb

### Шаги установки
```bash
# Pull официального образа Timeweb CLI
docker pull timeweb/cli

# Создание алиаса для удобства
alias twc='docker run -it --rm timeweb/cli'

# Авторизация
docker run -it --rm timeweb/cli login
```

## Способ 2: Установка через WSL

### Предварительные требования
- Windows 10/11 с включенным WSL2
- Установленный дистрибутив Ubuntu

### Шаги установки
```bash
# Обновление списка пакетов
sudo apt update

# Установка необходимых утилит
sudo apt install -y curl gpg

# Добавление GPG-ключа Timeweb
curl -fsSL https://repo.timeweb.cloud/gpg | sudo gpg --dearmor -o /usr/share/keyrings/timeweb-archive-keyring.gpg

# Добавление репозитория
echo "deb [signed-by=/usr/share/keyrings/timeweb-archive-keyring.gpg] https://repo.timeweb.cloud/debian stable main" | sudo tee /etc/apt/sources.list.d/timeweb.list

# Обновление списка пакетов
sudo apt update

# Установка Timeweb CLI
sudo apt install -y twc-cli

# Авторизация
twc login
```

## Способ 3: Кросс-платформенная установка (Python)

### Предварительные требования
- Python 3.8+
- pip

### Шаги установки
```bash
# Установка через pip
pip install timeweb-cli

# Или с использованием poetry
poetry add timeweb-cli
```

## Проверка установки
```bash
# Проверка версии
twc version

# Список доступных команд
twc help
```

## Troubleshooting
- Убедитесь, что у вас есть актуальный API-токен
- Проверьте подключение к интернету
- Обновите CLI до последней версии

**Внимание**: Всегда храните API-токены в безопасности!
