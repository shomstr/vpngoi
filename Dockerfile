FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/src:/app

# Копируем только requirements.txt первым — чтобы кэшировать зависимости
COPY requirements.txt .

# Устанавливаем зависимости (без --no-cache-dir для кэширования)
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Явно проверяем PyYAML — только если он НЕ в requirements.txt
# Если он там — уберите эту строку!
RUN pip install PyYAML==6.0.2 && \
    python -c "import yaml; print('PyYAML imported successfully')"

# Копируем весь проект — после установки зависимостей
COPY . .

# Устанавливаем проект в режиме разработки (если есть setup.py)
RUN if [ -f setup.py ]; then pip install -e .; fi

# Запуск
CMD ["python", "-m", "shop_bot"]