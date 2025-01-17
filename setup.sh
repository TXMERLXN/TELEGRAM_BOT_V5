#!/bin/bash

# Цвета для вывода
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Функция для проверки установленных программ
check_dependencies() {
    echo -e "${YELLOW}Проверка необходимых зависимостей...${NC}"
    
    # Проверка Docker
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}Docker не установлен. Пожалуйста, установите Docker.${NC}"
        exit 1
    fi

    # Проверка Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        echo -e "${RED}Docker Compose не установлен. Пожалуйста, установите Docker Compose.${NC}"
        exit 1
    fi

    echo -e "${GREEN}Все необходимые зависимости установлены.${NC}"
}

# Функция настройки окружения
setup_environment() {
    echo -e "${YELLOW}Настройка окружения...${NC}"

    # Проверка существования .env файла
    if [ ! -f .env ]; then
        echo -e "${YELLOW}Создание .env файла из шаблона...${NC}"
        cp .env.example .env
        echo -e "${GREEN}Файл .env создан. Отредактируйте его с вашими настройками.${NC}"
    else
        echo -e "${GREEN}.env файл уже существует.${NC}"
    fi
}

# Функция сборки и запуска проекта
build_and_run() {
    echo -e "${YELLOW}Сборка и запуск Docker контейнеров...${NC}"
    
    docker-compose down
    docker-compose build
    docker-compose up -d
    
    echo -e "${GREEN}Проект успешно запущен!${NC}"
}

# Основная функция
main() {
    check_dependencies
    setup_environment
    build_and_run
}

# Запуск основной функции
main
