FROM python:3.14.3-slim-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgomp1 \
    gosu \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ .
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

RUN useradd --create-home appuser \
    && chown -R appuser /app \
    && mkdir -p /data /db \
    && chown -R appuser /data /db

ARG SURFACE=cli
ENV SURFACE=${SURFACE}

ENTRYPOINT ["/entrypoint.sh"]