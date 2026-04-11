# Z-Image-Turbo

Local text-to-image generation using [Z-Image-Turbo](https://huggingface.co/Tongyi-MAI/Z-Image-Turbo).  
Includes a CLI tool, an OpenAI-compatible API server, and a web UI.

---

## Setup

```bash
./setup.sh
```

Creates `.venv/`, installs all dependencies (including diffusers from source), and makes the scripts executable.

---

## CLI

```bash
./zImageTurbo \
  -pass 9 \
  -seed 42 \
  -width 1024 \
  -height 1024 \
  -model ~/ML/Models/Tongyi-MAI/Z-Image-Turbo \
  -text "a black dog playing in the park"
```

**All flags:**

| Flag | Default | Description |
|------|---------|-------------|
| `-pass N` | `9` | Number of inference steps |
| `-seed N` | `-1` | Random seed (-1 = random) |
| `-width N` | `1024` | Output width in pixels |
| `-height N` | `1024` | Output height in pixels |
| `-model PATH` | `~/ML/Models/Tongyi-MAI/Z-Image-Turbo` | Model directory |
| `-text "..."` | required | Text prompt |
| `-output PATH` | `outputs/<ts>.png` | Custom output file path |
| `-cpu-offload` | off | Enable CPU offloading (saves memory) |

Generated images are saved to `outputs/`.

---

## Web UI + API Server

```bash
# Default port 7860
./serve --model ~/ML/Models/Tongyi-MAI/Z-Image-Turbo

# Custom port
./serve --model ~/ML/Models/Tongyi-MAI/Z-Image-Turbo --port 7860
```

Once running:
- **Web UI**: http://localhost:7860/
- **API**: http://localhost:7860/v1/images/generations
- **Models**: http://localhost:7860/v1/models
- **Health**: http://localhost:7860/health

---

## OpenWebUI Integration

1. In OpenWebUI → **Settings → Images → Image Generation**
2. Set engine to **OpenAI**
3. Set API base URL: `http://localhost:7860`
4. Set API key: `sk-local` (any string works)
5. Set model: `z-image-turbo`
6. Save and use the image generation button in chat

---

## API Reference

### `POST /v1/images/generations`

```json
{
  "prompt": "a sunset over the mountains",
  "size": "1024x1024",
  "num_steps": 9,
  "seed": 42,
  "response_format": "url"
}
```

Response:
```json
{
  "created": 1700000000,
  "elapsed_seconds": 12.4,
  "data": [
    { "url": "http://localhost:7860/outputs/zimg_1700000000_abc12345.png" }
  ]
}
```

Set `"response_format": "b64_json"` to receive the image as a base64-encoded PNG string instead.

---

## Model Notes

- Requires `ZImagePipeline` from latest diffusers (installed from source by `setup.sh`)
- Uses MPS on Apple Silicon, CUDA on NVIDIA GPU, or CPU fallback
- `guidance_scale` is fixed at `0.0` (required for Turbo variant)
- Recommended steps: 4–9
- Add `--cpu-offload` if you have limited unified memory

---

## Project Structure

```
z-image-turbo/
├── setup.sh          # One-time setup (venv + deps)
├── zImageTurbo       # CLI wrapper
├── serve             # Server wrapper
├── requirements.txt
├── src/
│   ├── generator.py  # Core generation logic
│   ├── cli.py        # CLI entry point
│   └── server.py     # Flask API + web UI server
├── templates/
│   └── index.html    # Web UI
├── static/
│   ├── css/style.css
│   └── js/app.js
└── outputs/          # Generated images (gitignored)
```
