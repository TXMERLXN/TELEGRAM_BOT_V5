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
  - `account_manager.py` - менеджер пула аккаунтов RunningHub
  - `task_queue.py` - управление очередью задач

### Используемые технологии

- Python 3.9+
- aiogram 3.x - асинхронный фреймворк для Telegram Bot API
- RunningHub API - сервис для обработки изображений с помощью ИИ
- aiohttp - асинхронный HTTP клиент

### Параметры конфигурации

- Токены и API ключи:
  - `BOT_TOKEN` - токен Telegram бота
    - Dev: `7875071911:AAFUbiivWfJr2E2Zhge4GCFWx5AacKzysmM`
    - Prod: `7612954390:AAGGCmH6M243P2URF7LNZ2xQNxeEWAkvCP8`
  - RunningHub аккаунты:
    - Аккаунт 1:
      - API ключ: `42bac06c90e448eeab2f5560d98d41b9`
      - Workflow ID: `1871659613585305601`
      - Макс. задач: 5
    - Аккаунт 2:
      - API ключ: `d99e6a6a59594042aded8909022840a8`
      - Workflow ID: `1878638674958061569`
      - Макс. задач: 5
    - Аккаунт 3:
      - API ключ: `4acad28f040a4fd7886db777287a9c00`
      - Workflow ID: `1878640309067489282`
      - Макс. задач: 5

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

## Ограничения и особенности

### RunningHub API
- RunningHub API имеет ограничение на одновременное выполнение задач
- Реализована поддержка множества аккаунтов для параллельной обработки
- При попытке создать несколько задач одновременно:
  - Задачи распределяются между доступными аккаунтами
  - Используется наименее загруженный аккаунт
  - Автоматическая балансировка нагрузки

### Обработка очереди задач
Для эффективной работы реализована система управления задачами:
- Автоматический выбор свободного аккаунта
- Отслеживание количества активных задач на каждом аккаунте
- Автоматическое освобождение аккаунта после завершения задачи
- Корректная обработка отмены генерации
- Graceful shutdown с отменой всех активных задач

### Рекомендации по использованию
- Система автоматически распределяет нагрузку между аккаунтами
- При получении сообщения о постановке в очередь - задача будет обработана следующим свободным аккаунтом
- Можно отменить задачу, находящуюся в очереди

## RunningHub API Documentation

### API Endpoints

#### Create Task
- **URL**: `/task/openapi/create`
- **Method**: POST
- **Parameters**:
  ```json
  {
    "apiKey": "your_api_key",
    "workflowId": "workflow_id",
    "inputs": {
      "2": "path/to/product.png",
      "32": "path/to/background.png"
    }
  }
  ```
- **Response**:
  ```json
  {
    "code": 0,
    "msg": "success",
    "data": {
      "taskId": "task_id",
      "clientId": "client_id",
      "taskStatus": "RUNNING",
      "promptTips": {
        "node_errors": {}
      }
    }
  }
  ```

#### Query Task Status
- **URL**: `/task/openapi/status`
- **Method**: POST
- **Parameters**:
  ```json
  {
    "taskId": "task_id",
    "apiKey": "your_api_key"
  }
  ```
- **Response**:
  ```json
  {
    "code": 0,
    "msg": "success",
    "data": "SUCCESS|FAIL|RUNNING|PENDING|QUEUED"
  }
  ```

#### Get Task Outputs
- **URL**: `/task/openapi/outputs`
- **Method**: POST
- **Parameters**:
  ```json
  {
    "taskId": "task_id",
    "apiKey": "your_api_key"
  }
  ```
- **Response**:
  ```json
  {
    "code": 0,
    "msg": "success",
    "data": [
      {
        "fileUrl": "https://output.url/image.png",
        "fileType": "png",
        "taskCostTime": "1"
      }
    ]
  }
  ```

### Error Codes
- `0`: Success
- `404`: Not Found
- `804`: Task is running (APIKEY_TASK_IS_RUNNING)
- `805`: Task is in queue (APIKEY_TASK_QUEUE)

### Task Status
- `SUCCESS`: Task completed successfully
- `FAIL`: Task failed
- `RUNNING`: Task is currently running
- `PENDING`: Task is pending
- `QUEUED`: Task is in queue

### Notes
1. All requests require an API key
2. File paths should be absolute paths on the server
3. Check task status periodically until it's SUCCESS or FAIL
4. Get outputs only when task status is SUCCESS
5. Handle rate limits and concurrent tasks per account

## Переменные окружения

Для работы бота необходимы следующие переменные окружения:

- `BOT_TOKEN` - токен Telegram бота
  - Dev: `7875071911:AAFUbiivWfJr2E2Zhge4GCFWx5AacKzysmM`
  - Prod: `7612954390:AAGGCmH6M243P2URF7LNZ2xQNxeEWAkvCP8`

- RunningHub аккаунты:
  ```env
  # Аккаунт 1
  RUNNINGHUB_API_KEY_1=42bac06c90e448eeab2f5560d98d41b9
  RUNNINGHUB_MAX_JOBS_1=5
  RUNNINGHUB_WORKFLOW_PRODUCT_1=1871659613585305601

  # Аккаунт 2
  RUNNINGHUB_API_KEY_2=d99e6a6a59594042aded8909022840a8
  RUNNINGHUB_MAX_JOBS_2=5
  RUNNINGHUB_WORKFLOW_PRODUCT_2=1878638674958061569

  # Аккаунт 3
  RUNNINGHUB_API_KEY_3=4acad28f040a4fd7886db777287a9c00
  RUNNINGHUB_MAX_JOBS_3=5
  RUNNINGHUB_WORKFLOW_PRODUCT_3=1878640309067489282
  ```

- Workflow Node IDs:
  ```env
  WORKFLOW_NODE_PRODUCT_PRODUCT_IMAGE=2
  WORKFLOW_NODE_PRODUCT_BACKGROUND_IMAGE=32
  ```

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
4. При общении с ботом используйте русский язык (если не указано иное)

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
