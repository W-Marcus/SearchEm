# SearchEm
A semantic search engine for local use. Simply drop your documents or images in a folder and let SearchEm figure out the rest.

## Usage

### Common options

| Flag | Short | Default | Description |
|------|-------|---------|-------------|
| `--dir` | `-d` | current directory (`os.getcwd()`) | Directory of files to embed |
| `--database` | `-db` | `<dir>/.SearchEm` | Database directory |
| `--extensions` | `-e` | from settings | File extensions to index e.g. `.jpg .png .pdf` |
| `--logging-path` | `-lp` | `<database>/logs` | Directory where log files will be written |
| `--model` | `-m` | `Qwen/Qwen3-VL-Embedding-2B` | HuggingFace model ID to use for embedding |

---

### CLI (`searchem_cli.py`)
```bash
python searchem_cli.py [options]
```

| Flag | Short | Default | Description |
|------|-------|---------|-------------|
| `--refresh` | `-r` | `False` | Embed new or changed files |
| `--update` | `-u` | `False` | Re-embed all files. Required when changing model |
| `--top-k` | `-k` | `5` | Number of results to return per query |

---

### REST API (`searchem_rest.py`)
```bash
python searchem_rest.py [options]
```

| Flag | Default | Description |
|------|---------|-------------|
| `--host` | `0.0.0.0` | Host to bind to |
| `--port` | `8000` | Port to listen on |
| `--reload` | `False` | Enable uvicorn auto-reload |
# SearchEm Docker Commands

## Build
```bash
docker compose build
```

## CLI
```bash
# Interactive session (index + search)
docker compose run --rm searchem-cli

# With flags
docker compose run --rm searchem-cli --refresh
docker compose run --rm searchem-cli --update
docker compose run --rm searchem-cli --top-k 10
```

## REST API
```bash
# Start in foreground
docker compose up searchem-rest

# Start in background
docker compose up -d searchem-rest

# Rebuild and restart after code changes
docker compose up --build searchem-rest
```

## Typical workflow
```bash
# 1. Build the index
docker compose run --rm searchem-cli --refresh

# 2. Serve queries
docker compose up -d searchem-rest
```

## Switching models

Re-embed everything with a different model using `--update` (required when changing models).

> `nomic-ai/nomic-embed-text-v2-moe` requires `trust_remote_code=True`
```bash
# CLI
docker compose run --rm searchem-cli --update --model nomic-ai/nomic-embed-text-v2-moe

# REST (pass model at server start)
docker compose up searchem-rest --model nomic-ai/nomic-embed-text-v2-moe
```
## Concurrent indexing

The index is protected by a file lock. Only one process may index at a time.
Running CLI `--refresh` and `POST /index` simultaneously is safe, however the second will fail.