FROM python:3.11-slim

# Installation de Chromium, de son Driver et des dépendances système Linux
RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Installation des packages Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copie du reste du code
COPY . .

# Lancement du bot
CMD ["python", "main.py"]
