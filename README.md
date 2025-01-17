# Telegram Bot V5

## Описание проекта
Telegram бот с расширенной функциональностью

## Требования
- Python 3.9+
- Telegram Bot API
- RunningHub API

## Деплой
[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/template/YOUR_TEMPLATE_ID)

### Настройка переменных окружения
1. Создайте `.env` файл на основе `.env.example`
2. Заполните необходимые переменные:
   - `BOT_TOKEN`: Токен Telegram бота
   - `RUNNINGHUB_API_KEY`: API ключ RunningHub
   - `WEBHOOK_HOST`: URL вашего Railway приложения

## Локальная разработка
1. Клонируйте репозиторий
2. Создайте виртуальное окружение: `python -m venv venv`
3. Активируйте виртуальное окружение:
   - Windows: `venv\Scripts\activate`
   - Linux/macOS: `source venv/bin/activate`
4. Установите зависимости: `pip install -r requirements.txt`
5. Запустите бота: `python bot_new.py`

## 🛠 Технологии
- **Язык**: Python 3.9+
- **Фреймворки**: 
  - Aiogram
  - Gunicorn
- **Деплой**: Railway
- **Управление зависимостями**: pip

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

## 📊 Производительность

- Автоматические тесты производительности
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
