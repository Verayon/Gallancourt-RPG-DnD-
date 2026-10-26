@echo off
cd /d "%~dp0.."
if not exist ".venv\Scripts\python.exe" (
    echo Ambiente virtual nao encontrado. Rode primeiro:
    echo   python -m venv .venv
    echo   .venv\Scripts\pip install -r requirements.txt
    pause
    exit /b 1
)
echo Abrindo o Painel do Mestre tambem para a rede e a Tailscale (nao so 127.0.0.1) ...
echo Acesse pelo IP ou nome Tailscale deste computador, na porta 5001.
echo Deixe esta janela aberta enquanto usa o painel.
set PAINEL_HOST=0.0.0.0
".venv\Scripts\python.exe" "admin\app.py"
pause
