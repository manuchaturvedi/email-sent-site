@echo off
echo ========================================
echo   Deploying to Raspberry Pi
echo ========================================
echo.

echo Connecting to Pi via SSH (port 8888)...
echo.

ssh -p 8888 manu@localhost "bash -c 'cd /home/manu/justmailit && git pull origin manu && docker restart justmailit-app && echo Deployment complete!'"

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================
    echo   Deployment Successful!
    echo ========================================
) else (
    echo.
    echo ========================================
    echo   Deployment Failed - Error Code: %ERRORLEVEL%
    echo ========================================
)

pause
