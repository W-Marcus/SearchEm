# SearchEm
A semantic search engine for local use. Simply drop your documents or images in a folder and let SearchEm figure out the rest.

## Usage

### In Brief
```bash
python app/searchem_rest.py --dir ./data --database ./data/searchem_db --model Qwen/Qwen3-VL-Embedding-2B --port 8000 --host 0.0.0.0
cd frontend && ng serve --port 4200
```

You can now access SearchEm on localhost:4200.

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

## Docker Commands Examples
Note that the initial build will likely be quite slow.
### Build and Run
```bash
docker compose up --build
```

### CLI
```bash
# Interactive search (REPL)
docker compose run --rm searchem-cli

# With flags
docker compose run --rm searchem-cli --refresh
docker compose run --rm searchem-cli --update
docker compose run --rm searchem-cli --top-k 10
```

### REST API
```bash
# Rebuild and start
docker compose up --build searchem-rest
```

### Switching models
Re-embed everything with a different model using `--update`.

## Concurrent indexing

The index is protected by a file lock. Only one process may index at a time.
Running CLI `--refresh` and `POST /index` simultaneously is safe, however the second will fail.