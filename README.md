# SearchEm
A semantic search engine for local use. Simply drop your documents or images in a folder and let SearchEm figure out the rest.

# Get running with Docker (compose)
`docker compose build`

`docker compose run --rm searchem --dir /data --database /db --refresh --model nomic-ai/nomic-embed-text-v2-moe`