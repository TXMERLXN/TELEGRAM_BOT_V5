<!-- CASCADE_GUIDELINES
This file contains critical project guidelines and rules.
AI assistants must check this file before making any changes to the project.
Version: 1.0
-->

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

## Архитектура проекта

### Структура файлов
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

### Окружения разработки

#### Development (dev)
- **Приложение**: `telegram-bot-v5-dev`
- **Бот**: @ai_da_dev_bot
- **Назначение**: Тестирование новых функций
- **Ветка**: `dev`
- **Хостинг**: Amvera

#### Production (prod)
- **Приложение**: `bot-v5-prod`
- **Бот**: @ai_da_master_bot
- **Назначение**: Рабочая версия для пользователей
- **Ветка**: `main`
- **Хостинг**: Amvera

### Процесс разработки

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

---

# Project Guidelines

## API Integration Rules

### RunningHub API
- **[CRITICAL]** ID узлов (nodeId) в RunningHub API являются уникальными для каждого воркфлоу и не должны изменяться без явного запроса. Значения в документации API служат только примером.
- Текущие ID узлов:
  - `nodeId: "2"` - узел для загрузки изображения продукта
  - `nodeId: "32"` - узел для загрузки фонового изображения

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

## Project Architecture
- Каждый аккаунт RunningHub может обрабатывать ограниченное количество задач одновременно
- Используется система очередей для распределения задач между аккаунтами

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

## Error Handling
- Все ошибки должны логироваться с полным стектрейсом
- Пользователю должны отправляться понятные сообщения об ошибках

## Security
- API ключи и другие чувствительные данные хранятся в файле `.env`
- SSL сертификаты должны проверяться в production окружении

---

# RunningHub API Documentation

## Overview
RunningHub API позволяет использовать функциональность ComfyUI, размещенную в облаке RunningHub. API поддерживает выполнение сложных рабочих процессов и последовательное выполнение задач.

## Endpoints

### 1. Upload Image
**POST** `/task/openapi/upload`
- Content-Type: multipart/form-data
- Parameters:
  - apiKey (string, required)
  - file (file, required, max 10MB)
  - fileType (string, required): "image", "video", "audio"
- Response:
  ```json
  {
    "code": 0,
    "msg": "success",
    "data": {
      "fileName": "api/filename.png",
      "fileType": "image"
    }
  }
  ```

### 2. Create Task
**POST** `/task/openapi/create`
- Content-Type: application/json
- Parameters:
  ```json
  {
    "workflowId": "string",
    "apiKey": "string",
    "nodeInfoList": [
      {
        "nodeId": "string",
        "fieldName": "string",
        "fieldValue": "string"
      }
    ]
  }
  ```
- Response:
  ```json
  {
    "code": 0,
    "msg": "success",
    "data": {
      "taskId": "string",
      "clientId": "string",
      "taskStatus": "RUNNING",
      "promptTips": "string"
    }
  }
  ```

### 3. Get Task Outputs
**POST** `/task/openapi/outputs`
- Content-Type: application/json
- Parameters:
  ```json
  {
    "taskId": "string",
    "apiKey": "string"
  }
  ```
- Response:
  ```json
  {
    "code": 0,
    "msg": "success",
    "data": [
      {
        "fileUrl": "string",
        "fileType": "string"
      }
    ]
  }
  ```

### 4. Check Account Status
**POST** `/uc/openapi/accountStatus`
- Content-Type: application/json
- Parameters:
  ```json
  {
    "apikey": "string"
  }
  ```
- Response:
  ```json
  {
    "code": 0,
    "msg": "success",
    "data": {
      "remainCoins": "string",
      "currentTaskCounts": "string"
    }
  }
  ```

### Error Codes
- `0`: Success
- `404`: Not Found
- `804`: Task is running (APIKEY_TASK_IS_RUNNING)
- `805`: Task is in queue (APIKEY_TASK_QUEUE)

### Task Status
- `QUEUED`: Задача в очереди
- `RUNNING`: Задача выполняется
- `SUCCESS`: Задача успешно завершена
- `FAILED`: Задача завершилась с ошибкой

## Important Notes
1. Воркфлоу должен быть успешно запущен хотя бы один раз вручную перед использованием через API
2. API не имеет отдельной системы биллинга - стоимость выполнения через API такая же, как и через веб-интерфейс
3. Для параллельного выполнения задач рекомендуется использовать пул API ключей от разных аккаунтов
4. При наличии нескольких save nodes в воркфлоу, API вернет массив результатов для каждого из них
