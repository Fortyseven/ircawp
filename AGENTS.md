# AGENTS.md — AI Assistant Context for ircawp

This file provides context for AI coding assistants working on the ircawp codebase.

## Project Overview

ircawp is an OpenAI-API-compatible IRC/Slack bot with plugin-based slash commands and LLM tool calling. It's designed for small-scale deployment on lower-end hardware.

**Stack:** Python 3.11+, FastAPI (media-server), Slack SDK, OpenAI-compatible API, `uv` package manager.

## Quick Start

```bash
# Setup
./setup.sh

# Run the bot
just run          # or: uv run -m app

# Run the media-server (needed for image generation)
just media-server # or: cd media-server && uv run -m uvicorn app.main:app --reload --port 8100

# Run tests
just test         # or: python -m pytest tests/ -v
just test-quick   # quick run
just test-cov     # with coverage report
```

## Architecture

The bot uses a **coordinator pattern** with decoupled services:

```
Ircawp (coordinator)
  ├── MessageRouter      — queue, dispatch, thread management
  ├── PluginManager      — plugin discovery & execution
  ├── MediaManager       — media file lifecycle
  ├── URLExtractor       — URL extraction & content fetching
  ├── Backend (OpenAI)   — LLM inference with tool calling
  ├── Frontend (Slack)   — Slack event handling
  └── MediaBackend       — HTTP client → media-server
```

**Media-server** is a separate FastAPI service for image generation:

- `POST /images/generations` — text-to-image (OpenAI-compatible)
- `POST /images/edits` — image editing
- Backends: flux2klein, zimageturbo, hyper_sdxl, sdxs, sd15, upscaler
- Config: `media-server/config.yml`

See `docs/ARCHITECTURE.md` for full diagrams and message flow.

## Key Directories

| Directory                    | Purpose                                            |
| ---------------------------- | -------------------------------------------------- |
| `app/`                       | Main bot application                               |
| `app/core/`                  | Core services (MessageRouter, PluginManager, etc.) |
| `app/backends/`              | LLM backends (OpenAI) + tool calling system        |
| `app/backends/tools/`        | LLM tools (auto-discovered from subdirs)           |
| `app/frontends/`             | Frontend implementations (Slack)                   |
| `app/plugins/`               | Slash command plugins (auto-discovered `*.py`)     |
| `app/media_backends/`        | HTTP client for media-server                       |
| `app/lib/`                   | Utilities (config, network, thread_history)        |
| `media-server/`              | Standalone image generation service                |
| `media-server/app/backends/` | Image generation backends                          |
| `tests/`                     | Pytest test suite                                  |
| `scripts/`                   | Utility scripts (tool_diag.py, etc.)               |
| `docs/`                      | Architecture and implementation docs               |

## Configuration

- **`config.yml`** — main bot config (frontend, backend, imagegen, LLM prompts, weather API)
- **`media-server/config.yml`** — media-server config (backend, port, per-backend settings)
- **`.env`** — Slack API credentials, secrets

Key config sections:

- `imagegen.backend` — which image backend (e.g. `flux2klein`)
- `imagegen.media_server_url` — URL of the media-server
- `openai.tools_enabled` — enable/disable LLM tool calling

## Plugin System

Plugins are `*.py` files in `app/plugins/` that export a `plugin` variable (a `PluginBase` instance). They're auto-discovered at startup.

**Plugin signature:**

```python
def main(prompt: str, media: list, backend, media_backend) -> tuple[str, str, bool, dict]:
    # Returns: (response_text, media_path, skip_imagegen, metadata)
```

See `app/plugins/__PluginBase.py` for the full interface. Examples: `8ball.py`, `weather.py`.

## LLM Tool Calling System

Tools are called autonomously by the LLM during inference (not via slash commands). They live in `app/backends/tools/<tool_name>/tool.py` and are auto-discovered.

**Tool interface:**

```python
from .ToolBase import ToolBase, ToolResult

class MyTool(ToolBase):
    name = "my_tool"
    description = "What this tool does"
    expertise_areas = ["category"]

    def execute(self, **kwargs) -> ToolResult:
        return ToolResult(text="result")

    def get_schema(self):
        # Return OpenAI function calling schema
```

See `app/backends/tools/README.md` and `docs/TOOL_CALLING_IMPLEMENTATION.md` for full docs.

## Message Flow

1. Frontend receives message → `ingestEvent()`
2. `Ircawp.ingestMessage()` → `MessageRouter.ingest()` (queued)
3. `MessageRouter._message_queue_loop()` processes:
    - Plugin command? → `PluginManager.execute_plugin()`
    - Text message → `URLExtractor.augment()` → `Backend.runInference()` (with tool calling)
4. `MediaManager.cleanup_media_files()`
5. `Ircawp._egest_message()` → `Frontend.egestEvent()` → user sees response

## Testing

- Tests use `pytest` with fixtures in `tests/conftest.py`
- Key fixtures: `mock_backend`, `mock_media_backend`, `mock_console`, `mock_plugin`, `mock_tool`
- Run: `just test` or `python -m pytest tests/ -v`

## Coding Conventions

- Python 3.11+ with type hints
- Pydantic models for request/response schemas (media-server)
- Rich console for structured logging
- Dependency injection — no global state or singletons
- Services receive dependencies via constructor
- Callback architecture — services don't depend on Ircawp directly

## Important Constraints

- The bot is designed for **small-scale** use (handful of users)
- Non-streaming responses — entire inference completes before posting
- Media-server is strictly prompt-in → image-out (no LLM logic)
- All prompt refinement happens in the main bot, not the media-server
