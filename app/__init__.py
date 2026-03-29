"""
SearchEm. Semantic search over local files.

app/
  searchem_cli.py          CLI entry point
  searchem_rest.py         REST entry point

  api/routes/              FastAPI route handlers
  core/                    Pure domain logic (no CLI/REST knowledge)
  models/common/           Shared Pydantic models
  models/cli/              CLI-specific models (Args)
  models/rest/             REST request/response schemas
  services/cli/            CLI orchestration (REPL)
  services/rest/           REST orchestration (SearchService, IndexService)
  config/                  Settings, logging setup
"""
