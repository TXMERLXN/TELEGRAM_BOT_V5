# Скрипт установки Docker Desktop в Windows

# Проверка прав администратора
if (-NOT ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Error "Запустите скрипт от имени администратора"
    exit 1
}

# Путь для загрузки установщика
$downloadDir = "$env:TEMP\DockerInstaller"
$installerPath = "$downloadDir\DockerDesktopInstaller.exe"

# Создание директории для загрузки
if (-Not (Test-Path -Path $downloadDir)) {
    New-Item -ItemType Directory -Path $downloadDir | Out-Null
}

# URL для скачивания Docker Desktop
$dockerUrl = "https://desktop.docker.com/win/main/amd64/Docker%20Desktop%20Installer.exe"

# Функция логирования
function Write-Log {
    param([string]$Message, [string]$Color = "Green")
    Write-Host "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $Message" -ForegroundColor $Color
}

# Скачивание установщика
try {
    Write-Log "Скачивание Docker Desktop..."
    Invoke-WebRequest -Uri $dockerUrl -OutFile $installerPath
    Write-Log "Загрузка завершена" -Color Cyan
}
catch {
    Write-Log "Ошибка загрузки: $_" -Color Red
    exit 1
}

# Установка Docker Desktop
try {
    Write-Log "Начало установки Docker Desktop..."
    Start-Process -FilePath $installerPath -ArgumentList "install --quiet" -Wait
    Write-Log "Установка завершена" -Color Green
}
catch {
    Write-Log "Ошибка установки: $_" -Color Red
    exit 1
}

# Проверка установки
try {
    $dockerVersion = docker --version
    Write-Log "Docker успешно установлен: $dockerVersion"
    
    # Тестовый запуск
    docker run hello-world
    Write-Log "Тестовый контейнер запущен успешно" -Color Green
}
catch {
    Write-Log "Ошибка проверки Docker: $_" -Color Yellow
}

# Очистка установщика
Remove-Item $installerPath -Force

# Рекомендации по завершению
Write-Log "Установка Docker Desktop завершена." -Color Magenta
Write-Log "Рекомендации:" -Color Cyan
Write-Log "1. Перезагрузите компьютер" -Color White
Write-Log "2. Откройте Docker Desktop и примите условия" -Color White
Write-Log "3. Включите WSL 2 в настройках" -Color White

# Открытие Docker Desktop
Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"
