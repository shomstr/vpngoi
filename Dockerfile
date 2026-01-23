FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/src:/app

# Установка системных зависимостей
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc \
        g++ \
        make \
        libffi-dev \
        libssl-dev \
        zlib1g-dev \
        libjpeg-dev \
        libpng-dev \
        freetype-dev \
        && rm -rf /var/lib/apt/lists/*

# Копируем requirements.txt
COPY requirements.txt .

# Устанавливаем зависимости
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Копируем весь проект
COPY . .

# Устанавливаем проект в режиме разработки (если есть setup.py)
RUN if [ -f setup.py ]; then pip install -e .; fi

# Запуск
CMD ["python", "-m", "shop_bot"]