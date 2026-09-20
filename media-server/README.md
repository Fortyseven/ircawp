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

- `qwenimage21` (default) — Qwen-Image-2.1, GGUF 4-bit transformer + 4-bit text encoder, max 1024px (see [docs/QWENIMAGE21.md](docs/QWENIMAGE21.md))
- `flux2klein` — max 1024px
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

backend: "qwenimage21"

backends:
    qwenimage21:
        max_output_size: 1024
        steps: 40
        gguf: "Abiray/Qwen-Image-2.1-GGUF/qwen_image_2.1_Q4_K_S.gguf"
        text_encoder_4bit: true
```

| Key              | Type   | Default        | Description                                          |
|------------------|--------|----------------|------------------------------------------------------|
| `server.host`    | string | `0.0.0.0`      | Bind address                                         |
| `server.port`    | int    | `8100`         | Port to listen on                                    |
| `backend`        | string | `qwenimage21`  | Default backend used when `model` is not specified   |

Generated images are stored in an OS-managed temporary directory and deleted immediately after encoding into the response. Per-backend settings under `backends.<id>` (e.g. `max_output_size`, `steps`, `gguf`) are passed to the backend at load time and with every request; request parameters (`size`, `quality`) override them.
