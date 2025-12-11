@echo off
title Weeek Integration Daemon
chcp 65001 >nul

REM Устанавливаем переменные окружения
set PROJECT_PATH=C:\weeek1
set PYTHON_EXE=python

echo ========================================
echo    WEEEK INTEGRATION DAEMON v2.0
echo    Автозапуск с обработкой ошибок
echo ========================================
echo Дата: %date%
echo Время: %time%
echo Python: %PYTHON_EXE%
echo.

REM Проверяем наличие Python
%PYTHON_EXE% --version >nul 2>&1
if errorlevel 1 (
    echo ОШИБКА: Python не установлен или не найден!
    echo Установите Python 3.8+ и добавьте в PATH
    pause
    exit /b 1
)

REM Переходим в папку проекта
if not exist "%PROJECT_PATH%" (
    echo ОШИБКА: Папка проекта не найдена: %PROJECT_PATH%
    pause
    exit /b 1
)

cd /d "%PROJECT_PATH%"

REM Проверяем наличие всех необходимых файлов
if not exist "daemon\weeek_daemon.py" (
    echo ОШИБКА: Основной файл демона не найден!
    dir daemon\
    pause
    exit /b 1
)

if not exist "integration\complete_integration.py" (
    echo ОШИБКА: Файл интеграции не найден!
    pause
    exit /b 1
)

echo Все файлы найдены, запускаю демона...
echo.

:start_daemon
cd daemon
echo [%time%] Запуск демона...
%PYTHON_EXE% weeek_daemon.py

REM Проверяем код возврата
if errorlevel 1 (
    echo.
    echo ========================================
    echo Демон завершился с ошибкой!
    echo Перезапуск через 30 секунд...
    echo ========================================
    timeout /t 30 /nobreak >nul
    goto start_daemon
) else (
    echo.
    echo ========================================
    echo Демон завершил работу нормально
    echo ========================================
)

pause