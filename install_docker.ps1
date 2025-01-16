# Скрипт установки Docker Desktop в Windows

# Проверка прав администратора
if (-NOT ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Error "Запустите скрипт от имени администратора"
    exit 1
}

# URL для скачивания Docker Desktop
$dockerUrl = "https://desktop.docker.com/win/main/amd64/Docker%20Desktop%20Installer.exe"
$installerPath = "$env:TEMP\DockerDesktopInstaller.exe"

# Скачивание установщика
Write-Host "Скачивание Docker Desktop..." -ForegroundColor Cyan
Invoke-WebRequest -Uri $dockerUrl -OutFile $installerPath

# Установка Docker Desktop
Write-Host "Установка Docker Desktop..." -ForegroundColor Yellow
Start-Process -FilePath $installerPath -ArgumentList "install --quiet" -Wait

# Проверка установки
try {
    $dockerVersion = docker --version
    Write-Host "Docker успешно установлен: $dockerVersion" -ForegroundColor Green
    
    # Первичная настройка
    docker run hello-world
}
catch {
    Write-Error "Ошибка установки Docker: $_"
}

# Очистка установщика
Remove-Item $installerPath -Force

Write-Host "Установка завершена. Перезагрузите компьютер." -ForegroundColor Green
