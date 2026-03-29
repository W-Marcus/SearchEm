FROM python:3.14.3-slim-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/*.py ./


RUN useradd --create-home appuser \
    && chown -R appuser /app \
    && mkdir -p /data /db \
    && chown -R appuser /data /db
USER appuser

ENTRYPOINT ["python", "searchem.py"]