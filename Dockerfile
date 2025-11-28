FROM python:3.11-slim

WORKDIR /app

# Copia requirements
COPY requirements.txt .

# Installa dipendenze
RUN pip install --no-cache-dir -r requirements.txt

# Copia il progetto
COPY . .

# Esponi porta per il server
EXPOSE 8000

# Avvia il server in modalità web
CMD ["flet", "run", "--web", "src/server.py"]
