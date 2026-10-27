@echo off
cd /d "%~dp0.."
if not exist ".venv\Scripts\python.exe" (
    echo Ambiente virtual nao encontrado. Rode primeiro:
    echo   python -m venv .venv
    echo   .venv\Scripts\pip install -r requirements.txt
    pause
    exit /b 1
)
echo Abrindo o site completo (wiki + Painel do Mestre) em http://127.0.0.1:5001/ ...
echo Deixe esta janela aberta enquanto usa o site.
".venv\Scripts\python.exe" "admin\app.py"
pause
