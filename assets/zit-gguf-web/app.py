import io
import os
import threading
from pathlib import Path
from typing import Optional

import torch
from fastapi import FastAPI, Form, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request

from diffusers import (
    ZImagePipeline,
    ZImageTransformer2DModel,
    GGUFQuantizationConfig,
)

APP_TITLE = "Z-Image Turbo Web"
APP_DIR = Path ("/srv/apps/zimage-turbo-web")
MODEL_DIR = Path("/srv/models/zImage-Turbo/gguf")
DEFAULT_REPO = "Tongyi-MAI/Z-Image-Turbo"

app = FastAPI(title=APP_TITLE)
templates = Jinja2Templates(directory=str(APP_DIR / "templates"))

# Simple in-memory cache for the currently loaded model/pipeline
_pipeline = None
_loaded_model_path = None
_pipeline_lock = threading.Lock()

# Choose dtype
if torch.cuda.is_available():
    DTYPE = torch.bfloat16
    DEVICE = "cuda"
else:
    DTYPE = torch.float32
    DEVICE = "cpu"


def list_gguf_models():
    if not MODEL_DIR.exists():
        return []
    return sorted([p.name for p in MODEL_DIR.glob("*.gguf")])


def load_pipeline(model_filename: str):
    global _pipeline, _loaded_model_path

    model_path = MODEL_DIR / model_filename
    if not model_path.exists():
        raise FileNotFoundError(f"Model not found: {model_path}")

    with _pipeline_lock:
        if _pipeline is not None and _loaded_model_path == str(model_path):
            return _pipeline

        # Free previous pipeline if switching models
        _pipeline = None
        _loaded_model_path = None
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

        _pipeline = pipe
        _loaded_model_path = str(model_path)
        return _pipeline


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    models = list_gguf_models()
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "models": models,
            "default_model": models[0] if models else "",
            "device": DEVICE,
            "dtype": str(DTYPE),
            "model_dir": str(MODEL_DIR),
        },
    )


@app.get("/api/models")
async def api_models():
    return {"models": list_gguf_models()}


@app.get("/health")
async def health():
    return JSONResponse(
        {
            "status": "ok",
            "cuda_available": torch.cuda.is_available(),
            "device": DEVICE,
            "dtype": str(DTYPE),
            "loaded_model": _loaded_model_path,
            "model_dir": str(MODEL_DIR),
        }
    )


@app.post("/generate")
async def generate(
    prompt: str = Form(...),
    model_filename: str = Form(...),
    width: int = Form(512),
    height: int = Form(512),
    seed: int = Form(42),
    passes: int = Form(9),
):
    if not prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt is required.")

    if width < 256 or width > 2048 or width % 8 != 0:
        raise HTTPException(status_code=400, detail="Width must be 256-2048 and divisible by 8.")
    if height < 256 or height > 2048 or height % 8 != 0:
        raise HTTPException(status_code=400, detail="Height must be 256-2048 and divisible by 8.")
    if passes < 1 or passes > 50:
        raise HTTPException(status_code=400, detail="Passes must be between 1 and 50.")

    try:
        pipe = load_pipeline(model_filename)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load model: {e}") from e

    try:
        generator = torch.Generator(device=DEVICE).manual_seed(seed)

        image = pipe(
            prompt=prompt,
            num_inference_steps=passes,
            guidance_scale=0.0,
            height=height,
            width=width,
            generator=generator,
        ).images[0]

        buf = io.BytesIO()
        image.save(buf, format="PNG")
        buf.seek(0)

        return StreamingResponse(
            buf,
            media_type="image/png",
            headers={
                "Cache-Control": "no-store",
                "Content-Disposition": 'inline; filename="generated.png"',
            },
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generation failed: {e}") from e
