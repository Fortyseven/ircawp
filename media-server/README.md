# ircawp Media Server

OpenAI-compatible image generation service for ircawp. Strictly prompt-in → image-out (no LLM logic).

## Endpoints

- `POST /images/generations` — text-to-image generation
- `POST /images/edits` — image editing with input images plus a text prompt
- `GET /health` — health check

### `POST /images/generations`

| Field     | Type   | Description                                                |
| --------- | ------ | ---------------------------------------------------------- |
| `prompt`  | string | Text description of the desired image (required)           |
| `model`   | string | Backend to use, e.g. `flux2klein` (optional, uses default) |
| `n`       | int    | Number of images (1-4, default 1)                          |
| `size`    | string | Output size as `WIDTHxHEIGHT`, e.g. `1024x1024`            |
| `quality` | string | `standard`, `hd`, `low`, `medium`, `high`, `auto`          |
| `user`    | string | End-user identifier (ignored)                              |

### `POST /images/edits`

All fields from `/images/generations`, plus:

| Field            | Type              | Description                                |
| ---------------- | ----------------- | ------------------------------------------ |
| `images`         | array of ImageRef | Input image(s) to edit (required)          |
| `input_fidelity` | string            | `high` or `low` fidelity to original input |
| `mask`           | ImageRef          | Mask image for inpainting                  |

Each `ImageRef` accepts `image_url` (base64 data URL).

### Response Format

Both endpoints return the same `ImagesResponse`:

```json
{
  "created": 1717689600,
  "data": [
    {
      "b64_json": "iVBORw0KGgoAAAANS...",
      "revised_prompt": "..."
    }
  ]
}
```

| Field            | Type     | Description                                        |
|------------------|----------|----------------------------------------------------|
| `created`        | int      | Unix timestamp (seconds) when the response was created |
| `data`           | array    | List of generated images                           |
| `data[].b64_json`| string   | Base64-encoded image data                          |
| `data[].revised_prompt` | string | Revised prompt used (optional, backend-dependent) |

## Backends

Available backends (set via `model` field or `config.yml`):

- `flux2klein` (default) — max 1024px
- `hyper_sdxl` — max 1024px
- `sd15` — max 512px
- `sdxs` — max 512px
- `zimageturbo` — max 1280px
- `upscaler` — image upscaling

## Run

```bash
cd media-server
uv run -m uvicorn app.main:app --reload --port 8100
```

Or via just:

```bash
just media-server
```

## Config

`config.yml` (YAML):

```yaml
server:
    host: "0.0.0.0"
    port: 8100

backend: "flux2klein"
```

| Key              | Type   | Default        | Description                                          |
|------------------|--------|----------------|------------------------------------------------------|
| `server.host`    | string | `0.0.0.0`      | Bind address                                         |
| `server.port`    | int    | `8100`         | Port to listen on                                    |
| `backend`        | string | `flux2klein`   | Default backend used when `model` is not specified   |

Generated images are stored in an OS-managed temporary directory and deleted immediately after encoding into the response. Per-backend settings (e.g. `max_output_size`) are hardcoded in each backend module, not read from config.
