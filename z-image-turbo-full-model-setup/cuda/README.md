# Z-Image-Turbo — CUDA (NVIDIA)

Identical to the macOS version but targets NVIDIA GPUs via CUDA 12.6.

Tested targets: **RTX 4090** (Ada Lovelace) · **RTX Pro 4000 Blackwell**

## Setup

```bash
./setup.sh
```

This installs PyTorch with `cu126` support. If your driver only supports CUDA 12.4, change the `--index-url` in `setup.sh` to `https://download.pytorch.org/whl/cu124`.

Verify CUDA after setup:
```bash
python -c "import torch; print(torch.cuda.get_device_name(0))"
```

## CLI

```bash
./zImageTurbo -pass 9 -seed 42 -width 1024 -height 1024 \
    -model ~/ML/Models/Tongyi-MAI/Z-Image-Turbo \
    -text "a cat on a mountain"
```

## Server (OpenWebUI-compatible)

```bash
./serve --model ~/ML/Models/Tongyi-MAI/Z-Image-Turbo
```

- Web UI: `http://localhost:7860/`
- API: `http://localhost:7860/v1/images/generations`
- OpenWebUI: Image Generation > OpenAI → `http://localhost:7860`

## Optional: xformers

For faster inference on large images, uncomment the xformers install line in `setup.sh` and re-run it:

```bash
pip install xformers
```

`generator.py` will auto-enable it if present.
