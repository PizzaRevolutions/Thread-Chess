FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

ENV FLET_FORCE_WEB_SERVER=true
CMD ["python", "-m", "flet", "src/server.py"]
