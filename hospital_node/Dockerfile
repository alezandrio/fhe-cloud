# Baixei para a versão 3.10 para garantir compatibilidade com a TenSEAL e PyTorch
FROM python:3.10-slim
WORKDIR /app
# Instalar os compiladores C++ necessários para a TenSEAL e outras dependências nativas
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
# Atualizar o PIP e instalar as bibliotecas
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python", "client.py"]