FROM python:3.11-slim

# Evita que o Python grave arquivos .pyc no disco e força o output no terminal (sem buffer)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    # Configurações do Poetry
    POETRY_VERSION=1.8.3 \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_NO_INTERACTION=1

# Dependências de sistema: tesseract + idiomas + poppler (pdfplumber)
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-por \
    tesseract-ocr-eng \
    poppler-utils \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

# Instala o Poetry
RUN pip install "poetry==$POETRY_VERSION"

WORKDIR /app

# Copia apenas os arquivos de dependência primeiro (para otimizar o cache do Docker)
COPY pyproject.toml poetry.lock* ./

# Regenerate lock file if pyproject.toml has changed
RUN poetry lock --no-update

# Instala as dependências do projeto (sem o código da aplicação por enquanto)
RUN poetry install --no-root

# Agora copia o restante do código da aplicação
COPY . .

EXPOSE 8000

# Como desativamos o ambiente virtual (POETRY_VIRTUALENVS_CREATE=false), 
# o uvicorn fica disponível globalmente no container.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]