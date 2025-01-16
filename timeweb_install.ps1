# Скрипт установки Timeweb CLI в Windows

# Проверка прав администратора
if (-NOT ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Error "Запустите скрипт от имени администратора"
    exit 1
}

# Функция проверки установленных компонентов
function Check-Dependency {
    param (
        [string]$Name,
        [scriptblock]$InstallScript
    )

    try {
        $result = Invoke-Expression "$Name --version"
        Write-Host "$Name уже установлен" -ForegroundColor Green
    }
    catch {
        Write-Host "$Name не найден. Установка..." -ForegroundColor Yellow
        & $InstallScript
    }
}

# Установка Docker
function Install-Docker {
    try {
        # Скачивание установщика Docker Desktop
        $dockerUrl = "https://desktop.docker.com/win/main/amd64/Docker%20Desktop%20Installer.exe"
        $dockerInstaller = "$env:TEMP\DockerDesktopInstaller.exe"
        
        Invoke-WebRequest -Uri $dockerUrl -OutFile $dockerInstaller
        
        # Тихая установка
        Start-Process -FilePath $dockerInstaller -ArgumentList "install --quiet" -Wait
        
        Write-Host "Docker успешно установлен" -ForegroundColor Green
    }
    catch {
        Write-Error "Ошибка установки Docker: $_"
    }
}

# Установка WSL
function Install-WSL {
    try {
        # Включение WSL
        dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart
        dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart
        
        # Установка WSL 2
        wsl --install -d Ubuntu
        
        Write-Host "WSL успешно установлен" -ForegroundColor Green
    }
    catch {
        Write-Error "Ошибка установки WSL: $_"
    }
}

# Установка Timeweb CLI через Docker
function Install-TimewebCLI-Docker {
    docker pull timeweb/cli
    
    # Создание алиаса
    Set-Alias -Name twc -Value "docker run -it --rm timeweb/cli"
    
    Write-Host "Timeweb CLI установлен через Docker" -ForegroundColor Green
}

# Основной процесс установки
function Main {
    Write-Host "Установка Timeweb CLI" -ForegroundColor Cyan
    
    # Проверка и установка зависимостей
    Check-Dependency -Name "docker" -InstallScript ${function:Install-Docker}
    Check-Dependency -Name "wsl" -InstallScript ${function:Install-WSL}
    
    # Установка Timeweb CLI
    Install-TimewebCLI-Docker
    
    # Справка
    Write-Host "`nИнструкция по использованию:" -ForegroundColor Yellow
    Write-Host "1. Запустите 'docker run -it --rm timeweb/cli login' для авторизации" -ForegroundColor Green
    Write-Host "2. Используйте 'twc' для выполнения команд" -ForegroundColor Green
}

# Запуск основного процесса
Main
