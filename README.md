# AI Product Photo Generator Bot

Telegram бот для генерации профессиональных фотографий продуктов с использованием искусственного интеллекта.

## 🚀 Быстрый старт

### Prerequisites
- Docker
- Docker Compose
- Telegram Bot Token
- RunningHub API Key

### Установка

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

3. Запустите проект
```bash
# Для Linux/macOS
./setup.sh

# Для Windows
.\setup.ps1
```

## 🛠 Технологии

- **Язык**: Python 3.9+
- **Фреймворки**: 
  - Aiogram
  - Sentry
  - Gunicorn
- **Деплой**: Docker, Docker Compose
- **CI/CD**: GitHub Actions

## 🔧 Возможности

- Генерация продуктовых фото с ИИ
- Многопоточная обработка задач
- Мониторинг производительности
- Автоматическое развертывание

## 📦 Структура проекта

- `bot_new.py`: Основной файл бота
- `config.py`: Конфигурация окружения
- `services/`: Сервисы интеграции
- `handlers/`: Обработчики команд
- `utils/`: Утилиты мониторинга и диагностики

## 🔒 Безопасность

- Защищенное webhook-соединение
- SSL-шифрование
- Мониторинг системных ресурсов
- Интеграция с Sentry для отслеживания ошибок

## 📊 Производительность

- Автоматические тесты производительности
- Кэширование Docker-слоев
- Оптимизация системных ресурсов

## 🤝 Contributing

1. Fork репозитория
2. Создайте feature-branch
3. Commit изменений
4. Push в branch
5. Создайте Pull Request

## 📄 Лицензия

[Укажите вашу лицензию]

## 📞 Поддержка

По всем вопросам: [ваш email или ссылка на issues]
