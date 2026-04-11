#!/usr/bin/env bash
set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$PROJECT_DIR/.venv"

echo "==> Setting up Z-Image-Turbo project at $PROJECT_DIR"

# Create venv
if [ ! -d "$VENV_DIR" ]; then
    echo "==> Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"
echo "==> Virtual environment activated: $VENV_DIR"

# Upgrade pip
pip install --upgrade pip

# Install PyTorch with MPS support (macOS)
echo "==> Installing PyTorch..."
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu 2>/dev/null || \
    pip install torch torchvision

# Install diffusers from source (required for ZImagePipeline)
echo "==> Installing diffusers from source (required for ZImagePipeline)..."
pip install git+https://github.com/huggingface/diffusers

# Install remaining requirements
echo "==> Installing other dependencies..."
pip install -r "$PROJECT_DIR/requirements.txt" --ignore-installed diffusers

# Make CLI executable
chmod +x "$PROJECT_DIR/zImageTurbo"

# Create outputs directory
mkdir -p "$PROJECT_DIR/outputs"

echo ""
echo "==> Setup complete!"
echo ""
echo "To activate the environment in future sessions:"
echo "  source $VENV_DIR/bin/activate"
echo ""
echo "CLI usage:"
echo "  ./zImageTurbo -pass 9 -seed 42 -width 1024 -height 1024 -model ~/ML/Models/Tongyi-MAI/Z-Image-Turbo -text \"a cat on a mountain\""
echo ""
echo "Server usage:"
echo "  python src/server.py --model ~/ML/Models/Tongyi-MAI/Z-Image-Turbo"
