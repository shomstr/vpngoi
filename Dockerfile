FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1

# Копируем файлы проекта
COPY . .

# Создаем requirements.txt если его нет
RUN if [ ! -f requirements.txt ]; then \
    echo "aiogram==3.21.0" > requirements.txt && \
    echo "flask==3.1.1" >> requirements.txt && \
    echo "py3xui==0.4.0" >> requirements.txt && \
    echo "pyotp==2.9.0" >> requirements.txt && \
    echo "python-dotenv==1.1.1" >> requirements.txt && \
    echo "qrcode[pil]==8.2" >> requirements.txt && \
    echo "yookassa==3.5.0" >> requirements.txt && \
    echo "aiosend==3.0.4" >> requirements.txt && \
    echo "aiohttp==3.9.5" >> requirements.txt && \
    echo "aiohttp-sse-client==0.2.1" >> requirements.txt && \
    echo "pytonconnect==0.3.2" >> requirements.txt && \
    echo "PyYAML==6.0.2" >> requirements.txt; \
    fi

# Устанавливаем зависимости
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Указываем путь для поиска модулей
ENV PYTHONPATH=/app

CMD ["python", "-m", "shop_bot"]