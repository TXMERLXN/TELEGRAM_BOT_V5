# Project Guidelines

## API Integration Rules

### RunningHub API
- **[CRITICAL]** ID узлов (nodeId) в RunningHub API являются уникальными для каждого воркфлоу и не должны изменяться без явного запроса. Значения в документации API служат только примером.
- Текущие ID узлов:
  - `nodeId: "2"` - узел для загрузки изображения продукта
  - `nodeId: "32"` - узел для загрузки фонового изображения

## Project Architecture
- Каждый аккаунт RunningHub может обрабатывать ограниченное количество задач одновременно
- Используется система очередей для распределения задач между аккаунтами

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

## Important Notes
1. Воркфлоу должен быть успешно запущен хотя бы один раз вручную перед использованием через API
2. API не имеет отдельной системы биллинга - стоимость выполнения через API такая же, как и через веб-интерфейс
3. Для параллельного выполнения задач рекомендуется использовать пул API ключей от разных аккаунтов
4. При наличии нескольких save nodes в воркфлоу, API вернет массив результатов для каждого из них
