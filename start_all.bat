@echo off
:: start_all.bat - запускает всю систему
chcp 65001 >nul
cd /d "%~dp0"

echo ========================================
echo     WEEEK INTEGRATION SYSTEM
echo ========================================
echo.

:: Запускаем демона
echo [1/2] Запускаем демона мониторинга...
start "Weeek Daemon" cmd /k "cd daemon && python weeek_daemon.py"

timeout /t 3 /nobreak >nul

:: Тестируем Telegram
echo [2/2] Тестируем Telegram уведомления...
cd telegram
python test_telegram.py

echo.
echo ✅ Система запущена!
echo 📁 Структура:
echo    daemon/       - демон и логи
echo    telegram/     - уведомления
echo    integration/  - логика Gmail->Weeek
pause