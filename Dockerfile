FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1

# Копируем requirements.txt
COPY requirements.txt .

# Устанавливаем зависимости в системе (не в venv)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Явно проверяем установку PyYAML
RUN pip install --no-cache-dir PyYAML==6.0.2 && \
    python -c "import yaml; print(f'PyYAML импортирован как yaml, версия установлена')"

# Копируем весь проект
COPY . .

# Устанавливаем проект в режиме разработки (если есть setup.py)
# Если нет setup.py, просто устанавливаем зависимости
RUN if [ -f setup.py ]; then pip install -e .; fi

# Устанавливаем PYTHONPATH чтобы видеть src/
ENV PYTHONPATH=/app/src:/app

# Запускаем из правильного пути
WORKDIR /app
CMD ["python", "-m", "shop_bot"]
