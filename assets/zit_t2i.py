#!/usr/bin/env python3
import argparse
import torch
from diffusers import ZImagePipeline
from datetime import datetime

def pick_device():
    if torch.backends.mps.is_available():
        return "mps"
    if torch.cuda.is_available():   # NVIDIA CUDA or AMD ROCm (HIP backend)
        return "cuda"
    return "cpu"

def safe_dtype_for(device: str):
    # Most conservative defaults to avoid black outputs:
    # - MPS: float32 is typically safer than float16 for many pipelines
    # - ROCm/CUDA: float16 is usually fine, but switch to float32 if black persists
    if device == "mps":
        return torch.float32
    if device == "cuda":
        return torch.bfloat16
    return torch.float32

def main():
    start_time = datetime.now()
    p = argparse.ArgumentParser(description="Z-Image-Turbo CLI (text-to-image)")
    p.add_argument("--prompt", required=True)
    p.add_argument("--negative", default="")
    p.add_argument("--out", default="zimage.png")
    p.add_argument("--steps", type=int, default=6)
    p.add_argument("--cfg", type=float, default=1.0)  # avoid 0 while debugging
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--w", type=int, default=768)
    p.add_argument("--h", type=int, default=768)
    p.add_argument("--force-fp32", action="store_true")
    args = p.parse_args()

    device = pick_device()
    dtype = torch.float32 if args.force_fp32 else safe_dtype_for(device)

    pipe = ZImagePipeline.from_pretrained(
        "Z-Image-Turbo",
        torch_dtype=dtype,
        low_cpu_mem_usage=False,
    ).to(device)

    # avoid inference_mode while debugging black images
    # (some stacks had black-image regressions around inference+compile combos)
    # see: pytorch issue reports
    gen_device = "cpu" if device == "mps" else device
    g = torch.Generator(device=gen_device).manual_seed(args.seed)

    with torch.no_grad():
        out = pipe(
            prompt=args.prompt,
            negative_prompt=args.negative if args.negative else None,
            num_inference_steps=args.steps,
            guidance_scale=args.cfg,
            width=args.w,
            height=args.h,
            generator=g,
        )
    image = out.images[0]
    image.save(args.out)

    print(f"Device={device} dtype={dtype} saved={args.out} took={datetime.now()-start_time}")
    if torch.cuda.is_available():
        print("torch.version.hip =", getattr(torch.version, "hip", None), "torch.version.cuda =", torch.version.cuda)

if __name__ == "__main__":
    main()
