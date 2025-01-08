# AI Product Photo Generator Bot

Telegram бот для генерации профессиональных фотографий продуктов с использованием искусственного интеллекта.

## Описание проекта

Бот позволяет создавать качественные продуктовые фотографии путем замены фона на более подходящий с помощью ИИ. Пользователь отправляет фотографию своего продукта и референс желаемого фона, а бот генерирует новое изображение, интегрируя продукт в выбранное окружение.

## Основные функции

- 📷 **Генерация фото продукта**
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
- [ ] Улучшение качества генерации
- [ ] Оптимизация времени обработки
- [ ] Добавление статистики использования

## Контакты

По всем вопросам обращайтесь к разработчикам проекта.
