@echo off
echo Проверка установки Docker...

where docker >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo Docker не установлен. Запустите установщик Docker Desktop.
    start https://www.docker.com/products/docker-desktop
    pause
    exit /b 1
)

docker --version
docker info

echo Попытка загрузки образа Timeweb CLI...
docker pull timeweb/cli

if %ERRORLEVEL% equ 0 (
    echo Образ Timeweb CLI успешно загружен
) else (
    echo Ошибка загрузки образа
)

pause
