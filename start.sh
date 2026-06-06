#!/bin/bash

# Muda para o diretório de onde o script está sendo executado
cd "$(dirname "$0")" || exit

echo "Configurando o Poetry para usar a pasta .venv local..."
poetry config virtualenvs.in-project true

echo "Verificando e instalando dependências com o Poetry..."
poetry install

# Verifica se o arquivo .env não existe
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "Arquivo .env criado a partir de .env.example -- adicione sua GEMINI_API_KEY"
fi

echo "Iniciando servidor em http://localhost:8000"
poetry run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000