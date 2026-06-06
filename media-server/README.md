# ircawp Media Server

Image generation HTTP service for ircawp. Strictly prompt-in → image-out (no LLM logic).

## Endpoints

- `POST /generate` — Generate an image
- `GET /health` — Health check
- `GET /image/{filename}` — Serve a generated image

## Run

```bash
uv run -m uvicorn app.main:app --reload --port 8100
```

## Config

Edit `config.yml` to set backend, port, and output directory.
