@echo off
setlocal enabledelayedexpansion

cd /d "%~dp0"

echo Configurando o Poetry para usar a pasta .venv local...
call poetry config virtualenvs.in-project true

echo Verificando e instalando dependencias com o Poetry...
call poetry install

if not exist ".env" (
    copy .env.example .env
    echo Arquivo .env criado a partir de .env.example -- adicione sua GEMINI_API_KEY
)

echo Iniciando servidor em http://localhost:8000
call poetry run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000