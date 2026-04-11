"""
Z-Image-Turbo Flask server.

Provides:
  GET  /                          Web UI
  POST /v1/images/generations     OpenAI-compatible image generation endpoint
  GET  /v1/models                 List available models (for OpenWebUI)
  GET  /outputs/<filename>        Serve generated images

OpenWebUI integration:
  Image Generation > OpenAI  ->  http://localhost:7860  (no trailing slash)
  API Key: any string (not validated)
  Model: z-image-turbo

Usage:
  python src/server.py --model ~/ML/Models/Tongyi-MAI/Z-Image-Turbo
"""

import argparse
import base64
import io
import os
import sys
import time
import uuid
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory, render_template
from flask_cors import CORS

# Allow running from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

app = Flask(
    __name__,
    template_folder=str(Path(__file__).parent.parent / "templates"),
    static_folder=str(Path(__file__).parent.parent / "static"),
)
CORS(app)

# Global generator instance (loaded at startup)
_generator = None
_model_path = None

OUTPUTS_DIR = Path(__file__).parent.parent / "outputs"
OUTPUTS_DIR.mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# Web UI
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/outputs/<path:filename>")
def serve_output(filename: str):
    return send_from_directory(str(OUTPUTS_DIR), filename)


# ---------------------------------------------------------------------------
# OpenAI-compatible endpoints
# ---------------------------------------------------------------------------

@app.route("/v1/models", methods=["GET"])
def list_models():
    """Return a minimal model list so OpenWebUI can confirm connectivity."""
    return jsonify({
        "object": "list",
        "data": [
            {
                "id": "z-image-turbo",
                "object": "model",
                "created": 1700000000,
                "owned_by": "tongyi-mai",
            }
        ],
    })


@app.route("/v1/images/generations", methods=["POST"])
def generate_image():
    """
    OpenAI-compatible image generation endpoint.

    Request body (JSON):
      {
        "prompt":           "...",          required
        "model":            "z-image-turbo" optional
        "n":                1,              optional (only 1 supported)
        "size":             "1024x1024",    optional  WxH
        "num_steps":        9,              optional  (non-standard extension)
        "seed":             -1,             optional  (non-standard extension)
        "response_format":  "url",          optional  "url" | "b64_json"
      }
    """
    if _generator is None:
        return jsonify({"error": {"message": "Model not loaded.", "type": "server_error"}}), 503

    data = request.get_json(force=True, silent=True) or {}

    prompt = data.get("prompt", "").strip()
    if not prompt:
        return jsonify({"error": {"message": "prompt is required.", "type": "invalid_request_error"}}), 400

    # Parse size ("WxH" or "W x H")
    size_str = data.get("size", "1024x1024").lower().replace(" ", "")
    try:
        w_str, h_str = size_str.split("x")
        width = int(w_str)
        height = int(h_str)
    except (ValueError, AttributeError):
        width, height = 1024, 1024

    num_steps    = int(data.get("num_steps", 9))
    seed         = int(data.get("seed", -1))
    response_fmt = data.get("response_format", "url")

    t0 = time.time()
    try:
        image = _generator.generate(
            prompt=prompt,
            width=width,
            height=height,
            num_steps=num_steps,
            seed=seed,
        )
    except Exception as exc:
        return jsonify({"error": {"message": str(exc), "type": "generation_error"}}), 500

    elapsed = time.time() - t0

    if response_fmt == "b64_json":
        buf = io.BytesIO()
        image.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
        image_data = {"b64_json": b64}
    else:
        # Save to disk and return a URL
        filename = f"zimg_{int(time.time())}_{uuid.uuid4().hex[:8]}.png"
        image.save(str(OUTPUTS_DIR / filename))
        host = request.host_url.rstrip("/")
        image_data = {"url": f"{host}/outputs/{filename}"}

    return jsonify({
        "created": int(time.time()),
        "elapsed_seconds": round(elapsed, 2),
        "data": [image_data],
    })


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "model_loaded": _generator is not None})


# ---------------------------------------------------------------------------
# Startup & CLI
# ---------------------------------------------------------------------------

def load_generator(model_path: str, cpu_offload: bool):
    global _generator, _model_path
    from src.generator import ZImageGenerator
    _model_path = model_path
    _generator = ZImageGenerator(
        model_path=model_path,
        cpu_offload=cpu_offload,
    )


def main():
    parser = argparse.ArgumentParser(description="Z-Image-Turbo API server")
    parser.add_argument("--model", default="~/ML/Models/Tongyi-MAI/Z-Image-Turbo",
                        help="Path to model directory")
    parser.add_argument("--cpu-offload", action="store_true",
                        help="Enable CPU offloading for low-memory devices")
    parser.add_argument("--port", type=int, default=7860,
                        help="Port to listen on (default: 7860)")
    parser.add_argument("--host", default="0.0.0.0",
                        help="Host to bind to (default: 0.0.0.0)")
    parser.add_argument("--lazy", action="store_true",
                        help="Skip model preloading; load on first request")
    args = parser.parse_args()

    model_path = os.path.expanduser(args.model)
    if not os.path.exists(model_path):
        print(f"[ERROR] Model path not found: {model_path}", file=sys.stderr)
        sys.exit(1)

    if not args.lazy:
        print(f"Loading model: {model_path}")
        load_generator(model_path, args.cpu_offload)

    print(f"\nZ-Image-Turbo server starting on http://{args.host}:{args.port}")
    print(f"  Web UI  :  http://localhost:{args.port}/")
    print(f"  API     :  http://localhost:{args.port}/v1/images/generations")
    print(f"  Models  :  http://localhost:{args.port}/v1/models")
    print()

    app.run(host=args.host, port=args.port, debug=False, threaded=False)


if __name__ == "__main__":
    main()
