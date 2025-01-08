# AI Product Photo Generator Bot

Telegram бот для генерации профессиональных фотографий продуктов с использованием искусственного интеллекта.

## Описание проекта

Бот позволяет создавать качественные продуктовые фотографии путем замены фона на более подходящий с помощью ИИ. Пользователь отправляет фотографию своего продукта и референс желаемого фона, а бот генерирует новое изображение, интегрируя продукт в выбранное окружение.

## Основные функции

- **Генерация фото продукта**
  - Загрузка фотографии продукта
  - Загрузка референса фона/окружения
  - Генерация нового изображения с помощью ИИ
  - Возможность повторной генерации

## Технические детали

### Архитектура

- `bot.py` - основной файл бота
- `config.py` - конфигурация и переменные окружения
- `messages.py` - текстовые сообщения и шаблоны
- `keyboards.py` - клавиатуры и кнопки интерфейса
- `handlers/` - обработчики команд и сообщений
  - `base.py` - базовые обработчики
  - `generation.py` - обработчики генерации изображений
- `services/` - внешние сервисы
  - `runninghub.py` - интеграция с RunningHub API

### Используемые технологии

- Python 3.9+
- aiogram 3.x - асинхронный фреймворк для Telegram Bot API
- RunningHub API - сервис для обработки изображений с помощью ИИ
- aiohttp - асинхронный HTTP клиент

### Параметры конфигурации

- `TG_BOT_TOKEN` - токен Telegram бота
- `RUNNINGHUB_API_KEY` - ключ API для RunningHub
- Таймауты для HTTP запросов:
  - Общий таймаут: 10 минут
  - Таймаут на подключение: 1 минута
  - Таймаут на чтение: 5 минут

## Окружения разработки

### Development (dev)
- **Приложение**: `telegram-bot-v5-dev`
- **Бот**: @ai_da_dev_bot
- **Назначение**: Тестирование новых функций
- **Ветка**: `dev`
- **Хостинг**: Amvera

### Production (prod)
- **Приложение**: `bot-v5-prod`
- **Бот**: @ai_da_master_bot
- **Назначение**: Рабочая версия для пользователей
- **Ветка**: `main`
- **Хостинг**: Amvera

## Процесс разработки

1. **Разработка новых функций**
   - Создание ветки от `dev`
   - Разработка и тестирование
   - Merge в `dev`

2. **Деплой в dev-окружение**
   - Переключиться на ветку `master`: `git checkout master`
   - Смержить изменения из `dev`: `git merge dev --no-ff`
   - Отправить изменения в Amvera: `git push amvera master`
   - Дождаться автоматического деплоя

3. **Выпуск в production**
   - Проверка работоспособности в dev
   - Merge `dev` в `main`
   - Автоматический деплой в prod-окружение

## Переменные окружения

Для работы бота необходимы следующие переменные окружения:

- `BOT_TOKEN` - токен Telegram бота
  - Dev: `7875071911:AAFUbiivWfJr2E2Zhge4GCFWx5AacKzysmM`
  - Prod: `7612954390:AAGGCmH6M243P2URF7LNZ2xQNxeEWAkvCP8`

- `RUNNINGHUB_API_KEY` - ключ API для RunningHub
  - Dev/Prod: `42bac06c90e448eeab2f5560d98d41b9`

## Мониторинг и логи

- Логирование реализовано с использованием стандартного модуля `logging`
- Основные события:
  - Старт бота и инициализация
  - Получение фотографий
  - Взаимодействие с RunningHub API
  - Ошибки и исключения

## Безопасность

- Переменные окружения хранятся в настройках Amvera
- Токены и ключи API не хранятся в коде
- Реализована валидация входных данных
- Обработка ошибок с информативными сообщениями

## Рекомендации по использованию

Для получения наилучших результатов:
1. Фотография продукта должна быть качественной и четкой
2. Фон на фотографии продукта должен быть однородным
3. Референс фона должен соответствовать желаемому результату

## Обработка ошибок

- Реализована система повторных попыток для HTTP запросов (до 3 попыток)
- Логирование ошибок и важных событий
- Информативные сообщения пользователю при возникновении проблем

## Планы по развитию

- [ ] Добавление новых стилей фотографий
- [ ] Улучшение качество генерации
- [ ] Оптимизация времени обработки
- [ ] Добавление статистики использования

## Контакты

По всем вопросам обращайтесь к разработчикам проекта.
