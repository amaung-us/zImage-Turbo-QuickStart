import base64
import io
import os
import threading
import time
from pathlib import Path
from typing import Optional

import torch
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Form, Header, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from starlette.requests import Request

from diffusers import (
    GGUFQuantizationConfig,
    ZImagePipeline,
    ZImageTransformer2DModel,
)

# --------------------------------------------------
# Load environment
# --------------------------------------------------
load_dotenv()

APP_DIR = Path(os.getenv("ZIMAGE_APP_DIR", "/srv/apps/zimage-turbo-web"))
MODEL_DIR = Path(os.getenv("ZIMAGE_MODEL_DIR", "/srv/models/z-image-turbo/gguf"))
DEFAULT_REPO = os.getenv("ZIMAGE_DEFAULT_REPO", "Tongyi-MAI/Z-Image-Turbo")
API_KEY = os.getenv("ZIMAGE_API_KEY", "change-me")
DEFAULT_WIDTH = int(os.getenv("ZIMAGE_DEFAULT_WIDTH", "512"))
DEFAULT_HEIGHT = int(os.getenv("ZIMAGE_DEFAULT_HEIGHT", "512"))
DEFAULT_STEPS = int(os.getenv("ZIMAGE_DEFAULT_STEPS", "9"))
DEFAULT_SEED = int(os.getenv("ZIMAGE_DEFAULT_SEED", "42"))
MAX_WIDTH = int(os.getenv("ZIMAGE_MAX_WIDTH", "2048"))
MAX_HEIGHT = int(os.getenv("ZIMAGE_MAX_HEIGHT", "2048"))
MAX_STEPS = int(os.getenv("ZIMAGE_MAX_STEPS", "50"))

# --------------------------------------------------
# FastAPI setup
# --------------------------------------------------
app = FastAPI(title="ZImage Turbo Web/API")
templates = Jinja2Templates(directory=str(APP_DIR / "templates"))

# --------------------------------------------------
# Runtime globals
# --------------------------------------------------
_pipe = None
_loaded_model = None
_pipe_lock = threading.Lock()

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
DTYPE = torch.bfloat16 if torch.cuda.is_available() else torch.float32


# --------------------------------------------------
# Helpers
# --------------------------------------------------
def list_models() -> list[str]:
    if not MODEL_DIR.exists():
        return []
    return sorted(p.name for p in MODEL_DIR.glob("*.gguf"))


def validate_dimensions(width: int, height: int) -> None:
    if width < 256 or width > MAX_WIDTH or width % 8 != 0:
        raise HTTPException(
            status_code=400,
            detail=f"Width must be between 256 and {MAX_WIDTH}, and divisible by 8.",
        )
    if height < 256 or height > MAX_HEIGHT or height % 8 != 0:
        raise HTTPException(
            status_code=400,
            detail=f"Height must be between 256 and {MAX_HEIGHT}, and divisible by 8.",
        )


def validate_steps(steps: int) -> None:
    if steps < 1 or steps > MAX_STEPS:
        raise HTTPException(
            status_code=400,
            detail=f"Steps must be between 1 and {MAX_STEPS}.",
        )


def check_api_key(authorization: Optional[str] = Header(default=None)) -> None:
    expected = f"Bearer {API_KEY}"
    if authorization != expected:
        raise HTTPException(status_code=401, detail="Invalid API key")


def load_pipeline(model_file: str):
    global _pipe, _loaded_model

    model_path = MODEL_DIR / model_file
    if not model_path.exists():
        raise FileNotFoundError(f"Model not found: {model_path}")

    with _pipe_lock:
        if _pipe is not None and _loaded_model == model_file:
            return _pipe

        _pipe = None
        _loaded_model = None

        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        transformer = ZImageTransformer2DModel.from_single_file(
            str(model_path),
            quantization_config=GGUFQuantizationConfig(compute_dtype=DTYPE),
            dtype=DTYPE,
        )

        pipe = ZImagePipeline.from_pretrained(
            DEFAULT_REPO,
            transformer=transformer,
            torch_dtype=DTYPE,
        )

        if torch.cuda.is_available():
            pipe.enable_model_cpu_offload()

        _pipe = pipe
        _loaded_model = model_file
        return _pipe


def generate_image_bytes(
    prompt: str,
    model: str,
    width: int,
    height: int,
    seed: int,
    steps: int,
) -> bytes:
    if not prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt is required.")

    validate_dimensions(width, height)
    validate_steps(steps)

    try:
        pipeline = load_pipeline(model)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load model: {e}") from e

    try:
        generator = torch.Generator(device=DEVICE).manual_seed(seed)

        image = pipeline(
            prompt=prompt,
            num_inference_steps=steps,
            guidance_scale=0.0,
            height=height,
            width=width,
            generator=generator,
        ).images[0]

        buf = io.BytesIO()
        image.save(buf, format="PNG")
        return buf.getvalue()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generation failed: {e}") from e


# --------------------------------------------------
# Web UI routes
# --------------------------------------------------
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    models = list_models()
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "models": models,
            "model_dir": str(MODEL_DIR),
            "default_width": DEFAULT_WIDTH,
            "default_height": DEFAULT_HEIGHT,
            "default_steps": DEFAULT_STEPS,
            "default_seed": DEFAULT_SEED,
            "device": DEVICE,
            "dtype": str(DTYPE),
        },
    )

@app.post("/generate")
async def generate(
    request: Request,
    prompt: str = Form(...),
    model: Optional[str] = Form(None),
    model_filename: Optional[str] = Form(None),
    width: int = Form(DEFAULT_WIDTH),
    height: int = Form(DEFAULT_HEIGHT),
    seed: int = Form(DEFAULT_SEED),
    passes: int = Form(DEFAULT_STEPS),
):
    raw_form = await request.form()
    print("RAW FORM:", dict(raw_form))

    selected_model = model or model_filename or raw_form.get("model") or raw_form.get("model_filename")

    if not selected_model:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Model is required",
                "received_keys": list(raw_form.keys()),
                "received_form": {k: str(v) for k, v in raw_form.items()},
            },
        )

    png_bytes = generate_image_bytes(
        prompt=prompt,
        model=selected_model,
        width=width,
        height=height,
        seed=seed,
        steps=passes,
    )

    return StreamingResponse(
        io.BytesIO(png_bytes),
        media_type="image/png",
        headers={
            "Cache-Control": "no-store",
            "Content-Disposition": 'inline; filename="generated.png"',
        },
    )

@app.get("/health")
async def health():
    return JSONResponse(
        {
            "status": "ok",
            "device": DEVICE,
            "dtype": str(DTYPE),
            "model_dir": str(MODEL_DIR),
            "models_found": list_models(),
            "loaded_model": _loaded_model,
        }
    )


# --------------------------------------------------
# OpenAI-compatible API routes
# --------------------------------------------------
@app.get("/v1/models", dependencies=[Depends(check_api_key)])
async def api_models():
    now = int(time.time())
    data = [
        {
            "id": model_name,
            "object": "model",
            "created": now,
            "owned_by": "zimage-local",
        }
        for model_name in list_models()
    ]
    return {"object": "list", "data": data}


@app.post("/v1/images/generations", dependencies=[Depends(check_api_key)])
async def api_generate_image(payload: dict):
    prompt = str(payload.get("prompt", "")).strip()
    model = payload.get("model")
    size = str(payload.get("size", f"{DEFAULT_WIDTH}x{DEFAULT_HEIGHT}")).lower()
    n = int(payload.get("n", 1))
    seed = int(payload.get("seed", DEFAULT_SEED))
    steps = int(payload.get("steps", DEFAULT_STEPS))
    response_format = str(payload.get("response_format", "b64_json")).lower()

    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt is required.")
    if not model:
        raise HTTPException(status_code=400, detail="Model is required.")
    if n != 1:
        raise HTTPException(status_code=400, detail="Only n=1 is supported.")
    if response_format not in {"b64_json"}:
        raise HTTPException(
            status_code=400,
            detail="Only response_format='b64_json' is supported.",
        )

    try:
        width_str, height_str = size.split("x")
        width = int(width_str)
        height = int(height_str)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail="size must look like '512x512'.",
        ) from e

    png_bytes = generate_image_bytes(
        prompt=prompt,
        model=model,
        width=width,
        height=height,
        seed=seed,
        steps=steps,
    )
    b64 = base64.b64encode(png_bytes).decode("utf-8")

    return {
        "created": int(time.time()),
        "data": [
            {
                "b64_json": b64,
            }
        ],
    }
