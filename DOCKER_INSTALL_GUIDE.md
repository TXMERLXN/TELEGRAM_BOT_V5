# Установка Docker Desktop в Windows

## Предварительные требования
- Windows 10/11 64-bit Pro, Enterprise, или Home
- Включенная виртуализация в BIOS
- Минимум 4 ГБ оперативной памяти

## Автоматическая установка
```powershell
# Запустите install_docker.bat от имени администратора
.\install_docker.bat
```

## Ручная установка
1. Скачайте установщик на [официальном сайте Docker](https://www.docker.com/products/docker-desktop)
2. Запустите установщик с правами администратора
3. Следуйте инструкциям мастера установки

## Проверка установки
```powershell
# Проверка версии Docker
docker --version

# Тестовый запуск контейнера
docker run hello-world
```

## Настройка
- Включите WSL 2 в настройках Docker Desktop
- Настройте ресурсы (CPU, RAM)
- Войдите в Docker Hub (опционально)

## Troubleshooting
- Включите виртуализацию в BIOS
- Обновите Windows
- Перезагрузите компьютер
- Переустановите WSL

## Безопасность
- Скачивайте Docker только с официального сайта
- Обновляйте до последней версии
- Используйте лицензионную версию Windows

## Настройка для Timeweb CLI
```powershell
# Загрузка образа Timeweb CLI
docker pull timeweb/cli

# Проверка образа
docker images | findstr timeweb
```

**Внимание**: Требуется перезагрузка компьютера!
