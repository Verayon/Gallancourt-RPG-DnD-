@echo off
cd /d "%~dp0.."
if not exist ".venv\Scripts\python.exe" (
    echo Ambiente virtual nao encontrado. Rode primeiro:
    echo   python -m venv .venv
    echo   .venv\Scripts\pip install -r requirements.txt
    pause
    exit /b 1
)
if not exist "admin\Caddyfile" (
    echo Nao encontrei admin\Caddyfile.
    echo Copie admin\Caddyfile.example para admin\Caddyfile e coloque seu dominio DDNS.
    pause
    exit /b 1
)
where caddy >nul 2>nul
if errorlevel 1 (
    echo Caddy nao encontrado no PATH. Instale com: winget install CaddyServer.Caddy
    pause
    exit /b 1
)
echo Iniciando o Painel (local) e o Caddy (HTTPS publico via DDNS) ...
echo Deixe esta janela aberta enquanto usa o site remotamente.
set PAINEL_HTTPS=1
start "Painel do Mestre - Flask" ".venv\Scripts\python.exe" "admin\app.py"
caddy run --config "admin\Caddyfile"
pause
