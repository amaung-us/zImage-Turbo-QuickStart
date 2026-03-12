#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# Universal Z-Image-Turbo setup script
# ============================================================

# -----------------------
# Defaults
# -----------------------
VENV_DIR="$HOME/venvs/zimage"
PYTHON_BIN="python3"

BACKEND="auto"            # auto|cuda|rocm|mps|cpu
CUDA_INDEX=""             # cu124, cu128, cu130
CUDA_INDEX_URL=""
BLACKWELL=0

ROCM_FORCE=0
ROCM72_FORCE=0

MODEL_DIFFUSERS_GIT="git+https://github.com/huggingface/diffusers"
EXTRA_PKGS="transformers accelerate safetensors pillow flask"

# ROCm 7.2 wheels (cp312 defaults)
ROCM72_TORCH_WHL_URL="https://repo.radeon.com/rocm/manylinux/rocm-rel-7.2/torch-2.9.1%2Brocm7.2.0.lw.git7e1940d4-cp312-cp312-linux_x86_64.whl"
ROCM72_VISION_WHL_URL="https://repo.radeon.com/rocm/manylinux/rocm-rel-7.2/torchvision-0.24.0%2Brocm7.2.0.gitb919bd0c-cp312-cp312-linux_x86_64.whl"
ROCM72_AUDIO_WHL_URL="https://repo.radeon.com/rocm/manylinux/rocm-rel-7.2/torchaudio-2.9.0%2Brocm7.2.0.gite3c6ee2b-cp312-cp312-linux_x86_64.whl"
ROCM72_TRITON_WHL_URL="https://repo.radeon.com/rocm/manylinux/rocm-rel-7.2/triton-3.5.1%2Brocm7.2.0.gita272dfa8-cp312-cp312-linux_x86_64.whl"

# -----------------------
# Helpers
# -----------------------
log() { printf "\n\033[1m==>\033[0m %s\n" "$*"; }
die() { echo "ERROR: $*" >&2; exit 2; }
have() { command -v "$1" >/dev/null 2>&1; }

# -----------------------
# CLI parsing
# -----------------------
while [[ $# -gt 0 ]]; do
  case "$1" in
    --blackwell)
      BLACKWELL=1
      BACKEND="cuda"
      ;;
    --cuda-index)
      CUDA_INDEX="$2"; BACKEND="cuda"; shift
      ;;
    --cuda-url)
      CUDA_INDEX_URL="$2"; BACKEND="cuda"; shift
      ;;
    --rocm)
      BACKEND="rocm"; ROCM_FORCE=1
      ;;
    --rocm72)
      BACKEND="rocm"; ROCM72_FORCE=1
      ;;
    --mps)
      BACKEND="mps"
      ;;
    --cpu)
      BACKEND="cpu"
      ;;
    --python)
      PYTHON_BIN="python$2"; shift
      ;;
    --venv)
      VENV_DIR="$2"; shift
      ;;
    -h|--help)
      cat <<EOF
Usage: $0 [options]

GPU options:
  --blackwell            Force NVIDIA Blackwell (CUDA cu130)
  --cuda-index cu130     Use specific CUDA wheel channel
  --cuda-url URL         Full CUDA wheel index URL override

ROCm options:
  --rocm                 Force ROCm backend
  --rocm72               Force ROCm 7.2 (Ryzen/Radeon wheels)

Other:
  --mps                  Force macOS Metal backend
  --cpu                  Force CPU-only
  --python 3.12          Force Python version
  --venv PATH            Virtualenv location

Examples:
  $0 --blackwell
  $0 --cuda-index cu130
  $0 --rocm72 --python 3.12
EOF
      exit 0
      ;;
    *)
      die "Unknown flag: $1"
      ;;
  esac
  shift
done

# -----------------------
# Detect backend if auto
# -----------------------
if [[ "$BACKEND" == "auto" ]]; then
  if [[ "$(uname)" == "Darwin" ]]; then
    BACKEND="mps"
  elif have nvidia-smi; then
    BACKEND="cuda"
  elif have rocminfo || [[ -d /opt/rocm ]]; then
    BACKEND="rocm"
  else
    BACKEND="cpu"
  fi
fi

log "Backend: $BACKEND"

# -----------------------
# Create venv
# -----------------------
log "Using Python: $PYTHON_BIN"
"$PYTHON_BIN" -V || die "Python not found"

if [[ ! -d "$VENV_DIR" ]]; then
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

# shellcheck disable=SC1090
source "$VENV_DIR/bin/activate"
pip install -U pip wheel setuptools

pip uninstall -y torch torchvision torchaudio triton >/dev/null 2>&1 || true

# -----------------------
# Install torch
# -----------------------
case "$BACKEND" in
  cuda)
    if [[ "$BLACKWELL" == "1" && -z "$CUDA_INDEX" && -z "$CUDA_INDEX_URL" ]]; then
      CUDA_INDEX="cu130"
    fi

    if [[ -n "$CUDA_INDEX_URL" ]]; then
      IDX="$CUDA_INDEX_URL"
    else
      IDX="https://download.pytorch.org/whl/${CUDA_INDEX:-cu124}"
    fi

    log "Installing PyTorch CUDA from: $IDX"
    pip install -U torch torchvision torchaudio --index-url "$IDX"
    ;;
  rocm)
    if [[ "$ROCM72_FORCE" == "1" ]]; then
      log "Installing ROCm 7.2 wheels (repo.radeon.com)"
      have wget || die "wget required"
      tmp="$(mktemp -d)"
      pushd "$tmp" >/dev/null
      wget -q "$ROCM72_TORCH_WHL_URL"
      wget -q "$ROCM72_VISION_WHL_URL"
      wget -q "$ROCM72_AUDIO_WHL_URL"
      wget -q "$ROCM72_TRITON_WHL_URL"
      pip install ./*.whl
      popd >/dev/null
      rm -rf "$tmp"
    else
      log "Installing ROCm wheels from PyTorch host"
      pip install -U torch torchvision torchaudio --index-url https://download.pytorch.org/whl/rocm6.2
    fi
    ;;
  mps|cpu)
    log "Installing CPU/MPS PyTorch"
    pip install -U torch torchvision torchaudio
    ;;
esac

# -----------------------
# Diffusers + deps
# -----------------------
pip install -U "$MODEL_DIFFUSERS_GIT"
pip install -U $EXTRA_PKGS

# -----------------------
# Verification
# -----------------------
log "Verification"
python - <<'PY'
import torch, platform
print("Platform:", platform.platform())
print("Torch:", torch.__version__)
print("CUDA:", torch.version.cuda)
print("HIP:", getattr(torch.version, "hip", None))
print("CUDA available:", torch.cuda.is_available())
if torch.cuda.is_available():
    print("Arch list:", torch.cuda.get_arch_list())
    print("GPU0:", torch.cuda.get_device_name(0))
has_mps = hasattr(torch.backends,"mps") and torch.backends.mps.is_available()
print("MPS available:", has_mps)
PY

log "Done"
log "Activate: source \"$VENV_DIR/bin/activate\""

