FROM python:3.10-slim

# Evita buffering en logs
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Instalar dependencias del sistema (para mysqlclient o cryptography)
RUN apt-get update && apt-get install -y \
    build-essential \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Comando para iniciar el bot
CMD ["python", "bot.py"]
