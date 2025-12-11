@echo off
echo Установка службы Weeek Integration...
echo.

REM Создаем службу через NSSM (нужно скачать nssm.exe)
if not exist nssm.exe (
    echo Скачивание NSSM...
    powershell -Command "Invoke-WebRequest -Uri 'https://nssm.cc/release/nssm-2.24.zip' -OutFile 'nssm.zip'"
    powershell -Command "Expand-Archive -Path 'nssm.zip' -DestinationPath '.'"
    copy "nssm-2.24\win64\nssm.exe" .
    rmdir /s /q nssm-2.24
    del nssm.zip
)

REM Устанавливаем службу
nssm install WeeekIntegration "C:\Python311\python.exe" "C:\weeek1\weeek_daemon.py"
nssm set WeeekIntegration Description "Автоматическая интеграция почты с Weeek каждые 10 минут"
nssm set WeeekIntegration AppDirectory "C:\weeek1"
nssm set WeeekIntegration AppStdout "C:\weeek1\logs\service.log"
nssm set WeeekIntegration AppStderr "C:\weeek1\logs\service_error.log"
nssm set WeeekIntegration Start SERVICE_AUTO_START

echo.
echo Служба установлена! Команды управления:
echo   net start WeeekIntegration    - запустить службу
echo   net stop WeeekIntegration     - остановить службу
echo   sc delete WeeekIntegration    - удалить службу
pause