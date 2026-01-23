FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/src:/app

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir PyYAML==6.0.2

COPY . .

RUN if [ -f setup.py ]; then pip install -e .; fi

CMD ["python", "-m", "shop_bot"]