FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1

# Устанавливаем Nginx
RUN apt-get update && apt-get install -y nginx && \
    rm -rf /var/lib/apt/lists/*

# Копируем requirements.txt
COPY requirements.txt .

# Устанавливаем зависимости
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Копируем весь проект
COPY . .

# Копируем конфиг Nginx (создадим его ниже)
COPY nginx.conf /etc/nginx/nginx.conf

# Устанавливаем PYTHONPATH
ENV PYTHONPATH=/app/src:/app

# Запускаем из правильного пути
WORKDIR /app
CMD ["sh", "-c", "nginx && python -m shop_bot"]