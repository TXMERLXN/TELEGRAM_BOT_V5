@echo off
setlocal enabledelayedexpansion

:: Проверка аргументов
if "%1"=="" (
    echo Использование: timeweb_docker_cli.bat [команда]
    echo Пример: timeweb_docker_cli.bat login
    exit /b 1
)

:: Функция выполнения команды в Docker
docker run -it --rm ^
    -v %USERPROFILE%/.twc:/root/.twc ^
    -v %CD%:/workdir ^
    -w /workdir ^
    timeweb/cli %*

exit /b 0
