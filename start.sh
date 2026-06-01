#!/bin/bash
set -e

cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
  echo "Criando ambiente virtual..."
  python3 -m venv .venv
fi

source .venv/bin/activate

echo "Instalando dependências..."
pip install -q -r requirements.txt

if [ ! -f ".env" ]; then
  cp .env.example .env
  echo "Arquivo .env criado a partir de .env.example — adicione sua GEMINI_API_KEY"
fi

HOST=${HOST:-0.0.0.0}
PORT=${PORT:-8000}

echo "Iniciando servidor em http://$HOST:$PORT"
uvicorn app.main:app --host "$HOST" --port "$PORT"