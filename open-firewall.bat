@echo off

:: Самоподъём до прав администратора
net session >nul 2>&1
if %errorlevel% neq 0 (
    powershell -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b
)

echo =============================================
echo  Открываем порт 8000 в брандмауэре Windows
echo =============================================
echo.

:: Удалить старое правило, если есть
netsh advfirewall firewall delete rule name="Project HTTP 8000" >nul 2>&1

:: Добавить новое
netsh advfirewall firewall add rule name="Project HTTP 8000" dir=in action=allow protocol=TCP localport=8000

if %errorlevel%==0 (
    echo.
    echo  Готово! Порт 8000 открыт.
    echo.
    echo  Откройте на телефоне:
    echo  http://192.168.1.11:8000/index.html
    echo.
) else (
    echo.
    echo  Что-то пошло не так. Попробуйте ещё раз.
    echo.
)

pause
