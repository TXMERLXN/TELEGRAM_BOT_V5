param(
    [switch]$Build = $false,
    [switch]$Run = $false
)

# Функция проверки зависимостей
function Check-Dependencies {
    Write-Host "Проверка необходимых зависимостей..." -ForegroundColor Yellow
    
    # Проверка Docker
    if (!(Get-Command docker -ErrorAction SilentlyContinue)) {
        Write-Host "Docker не установлен. Пожалуйста, установите Docker." -ForegroundColor Red
        exit 1
    }

    # Проверка Docker Compose
    if (!(Get-Command docker-compose -ErrorAction SilentlyContinue)) {
        Write-Host "Docker Compose не установлен. Пожалуйста, установите Docker Compose." -ForegroundColor Red
        exit 1
    }

    Write-Host "Все необходимые зависимости установлены." -ForegroundColor Green
}

# Функция настройки окружения
function Setup-Environment {
    Write-Host "Настройка окружения..." -ForegroundColor Yellow

    # Проверка существования .env файла
    if (!(Test-Path .env)) {
        Write-Host "Создание .env файла из шаблона..." -ForegroundColor Yellow
        Copy-Item .env.example .env
        Write-Host "Файл .env создан. Отредактируйте его с вашими настройками." -ForegroundColor Green
    }
    else {
        Write-Host ".env файл уже существует." -ForegroundColor Green
    }
}

# Функция сборки и запуска проекта
function Build-And-Run {
    Write-Host "Сборка и запуск Docker контейнеров..." -ForegroundColor Yellow
    
    docker-compose down
    docker-compose build
    docker-compose up -d
    
    Write-Host "Проект успешно запущен!" -ForegroundColor Green
}

# Основная функция
function Main {
    Check-Dependencies
    Setup-Environment
    
    if ($Build) {
        docker-compose build
    }
    
    if ($Run) {
        Build-And-Run
    }
}

# Запуск основной функции
Main
