#!/usr/bin/env bash
set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$PROJECT_DIR/.venv"

echo "==> Setting up Z-Image-Turbo (CUDA) at $PROJECT_DIR"

# Create venv
if [ ! -d "$VENV_DIR" ]; then
    echo "==> Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"
echo "==> Virtual environment activated: $VENV_DIR"

# Upgrade pip
pip install --upgrade pip

# Install PyTorch with CUDA 13.0 support
echo "==> Installing PyTorch with CUDA 13.0 support..."
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu130

# Install diffusers from source (required for ZImagePipeline)
echo "==> Installing diffusers from source (required for ZImagePipeline)..."
pip install git+https://github.com/huggingface/diffusers

# Install remaining requirements
echo "==> Installing other dependencies..."
pip install -r "$PROJECT_DIR/requirements.txt" --ignore-installed diffusers

# Optional: install xformers for memory-efficient attention
# Uncomment if you want faster inference on large images:
# echo "==> Installing xformers..."
# pip install xformers

# Make scripts executable
chmod +x "$PROJECT_DIR/zImageTurbo"
chmod +x "$PROJECT_DIR/serve"

# Create outputs directory
mkdir -p "$PROJECT_DIR/outputs"

echo ""
echo "==> Setup complete!"
echo ""
echo "To activate the environment in future sessions:"
echo "  source $VENV_DIR/bin/activate"
echo ""
echo "Verify CUDA is available:"
echo "  python -c \"import torch; print(torch.cuda.get_device_name(0))\""
echo ""
echo "CLI usage:"
echo "  ./zImageTurbo -pass 9 -seed 42 -width 1024 -height 1024 -model ~/ML/Models/Tongyi-MAI/Z-Image-Turbo -text \"a cat on a mountain\""
echo ""
echo "Server usage:"
echo "  ./serve --model ~/ML/Models/Tongyi-MAI/Z-Image-Turbo"
