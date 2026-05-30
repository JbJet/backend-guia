
@echo off
setlocal enabledelayedexpansion
 
cd /d "%~dp0"
 
if not exist ".venv" (
    echo Criando ambiente virtual...
    python -m venv .venv
)
 
call .venv\Scripts\activate.bat
 
echo Instalando dependencias...
pip install -q -r requirements.txt
 
if not exist ".env" (
    copy .env.example .env
    echo Arquivo .env criado a partir de .env.example -- adicione sua GEMINI_API_KEY
)
 
echo Iniciando servidor em http://localhost:8000
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
 