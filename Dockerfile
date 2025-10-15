FROM python:3.12-slim

WORKDIR /app

# Установка зависимостей
RUN pip install --no-cache-dir \
    websockets>=12.0 \
    python-dotenv>=1.0.0

# Копируем файлы приложения
COPY stomp_utils.py .
COPY monitor_1500.py .
COPY .env .

# Запуск
CMD ["python", "monitor_1500.py"]

