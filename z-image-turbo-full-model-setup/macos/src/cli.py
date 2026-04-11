"""
CLI entry point for Z-Image-Turbo.

Usage example:
  python src/cli.py -pass 9 -seed 42 -width 1024 -height 1024 \
      -model ~/ML/Models/Tongyi-MAI/Z-Image-Turbo \
      -text "a black dog playing in the park"
"""

import argparse
import os
import sys
import time
from pathlib import Path

# Allow running from project root without installing the package
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="zImageTurbo",
        description="Z-Image-Turbo: fast text-to-image generation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("-pass", dest="num_steps", type=int, default=9,
                   help="Number of inference steps (default: 9)")
    p.add_argument("-seed", dest="seed", type=int, default=-1,
                   help="Random seed (-1 = random, default: -1)")
    p.add_argument("-width", dest="width", type=int, default=1024,
                   help="Output image width in pixels (default: 1024)")
    p.add_argument("-height", dest="height", type=int, default=1024,
                   help="Output image height in pixels (default: 1024)")
    p.add_argument("-model", dest="model", type=str,
                   default="~/ML/Models/Tongyi-MAI/Z-Image-Turbo",
                   help="Path to the model (directory or .gguf file)")
    p.add_argument("-text", dest="text", type=str, required=True,
                   help="Text prompt for image generation")
    p.add_argument("-output", dest="output", type=str, default=None,
                   help="Output file path (default: outputs/<timestamp>.png)")
    p.add_argument("-cpu-offload", dest="cpu_offload", action="store_true",
                   help="Enable CPU offloading to reduce memory usage")
    return p


def main():
    parser = build_parser()

    # Support "model location <path>" syntax from the user's example by
    # treating bare positional tokens as a legacy model path override.
    argv = sys.argv[1:]
    # Normalize "model" "location" pair into "-model" if it appears as
    # positional tokens (legacy CLI style in the spec).
    cleaned = []
    i = 0
    while i < len(argv):
        if argv[i] == "model" and i + 1 < len(argv) and argv[i + 1] == "location":
            # Next token after "model location" is the path
            if i + 2 < len(argv):
                cleaned += ["-model", argv[i + 2]]
                i += 3
            else:
                i += 2
        else:
            cleaned.append(argv[i])
            i += 1

    args = parser.parse_args(cleaned)

    # Resolve model path
    model_path = os.path.expanduser(args.model)
    if not os.path.exists(model_path):
        print(f"[ERROR] Model path not found: {model_path}", file=sys.stderr)
        sys.exit(1)

    # Determine output path
    project_root = Path(__file__).parent.parent
    outputs_dir = project_root / "outputs"
    outputs_dir.mkdir(exist_ok=True)

    if args.output:
        output_path = Path(os.path.expanduser(args.output))
    else:
        ts = int(time.time())
        seed_tag = f"s{args.seed}" if args.seed >= 0 else "srnd"
        output_path = outputs_dir / f"zimg_{ts}_{seed_tag}.png"

    # Load model and generate
    from src.generator import ZImageGenerator

    print(f"[zImageTurbo]")
    print(f"  Prompt  : {args.text}")
    print(f"  Model   : {model_path}")
    print(f"  Size    : {args.width}x{args.height}")
    print(f"  Steps   : {args.num_steps}")
    print(f"  Seed    : {args.seed if args.seed >= 0 else 'random'}")
    print()

    generator = ZImageGenerator(
        model_path=model_path,
        cpu_offload=args.cpu_offload,
    )

    t0 = time.time()
    image = generator.generate(
        prompt=args.text,
        width=args.width,
        height=args.height,
        num_steps=args.num_steps,
        seed=args.seed,
    )
    elapsed = time.time() - t0

    image.save(str(output_path))
    print(f"\nGenerated in {elapsed:.1f}s  ->  {output_path}")


if __name__ == "__main__":
    main()
