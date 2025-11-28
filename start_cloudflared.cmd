@echo off
REM Start Cloudflare Tunnel for justmailit.in
cd /d "%USERPROFILE%\.cloudflared"
start /min "Cloudflared Tunnel" "%USERPROFILE%\cloudflared.exe" tunnel run justmailit
exit
