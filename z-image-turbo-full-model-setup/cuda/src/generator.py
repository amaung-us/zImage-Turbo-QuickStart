"""
Core image generation logic for Z-Image-Turbo (CUDA/NVIDIA).
"""

import os
from typing import Optional

from PIL import Image


def _get_device():
    """Return the best available CUDA device."""
    import torch
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"


class ZImageGenerator:

    def __init__(self, model_path: str, cpu_offload: bool = False):
        self.model_path = os.path.expanduser(model_path)
        self.cpu_offload = cpu_offload
        self.pipe = None
        self._load_model()

    def _load_model(self):
        import torch
        from diffusers import ZImagePipeline

        device = _get_device()

        # bfloat16 on CUDA: same exponent range as float32 so transformer
        # activations cannot overflow to NaN (float16 overflows at ~65504).
        # Throughput is identical to float16 on Ampere/Ada/Blackwell tensor cores.
        torch_dtype = torch.bfloat16 if device == "cuda" else torch.float32

        if device == "cuda":
            # Allow TF32 for matrix multiplications and convolutions — large
            # throughput gain on Ampere (RTX 30xx) / Ada (RTX 40xx) /
            # Blackwell (RTX Pro 4000) with negligible quality loss
            torch.backends.cuda.matmul.allow_tf32 = True
            torch.backends.cudnn.allow_tf32 = True

        print(f"Loading model from: {self.model_path}")
        print(f"  device={device}  dtype={torch_dtype}")

        self.pipe = ZImagePipeline.from_pretrained(
            self.model_path,
            torch_dtype=torch_dtype,
            local_files_only=True,
        )

        if self.cpu_offload or device == "cpu":
            self.pipe.enable_model_cpu_offload()
            print("  CPU offloading enabled.")
        else:
            self.pipe.to(device)

            # Enable memory-efficient attention if xformers is installed
            try:
                self.pipe.enable_xformers_memory_efficient_attention()
                print("  xformers memory-efficient attention enabled.")
            except Exception:
                pass

        # float16 VAE decoding can produce NaN/inf on CUDA, resulting in a
        # black image.  Cast VAE weights to float32 and wrap decode() so that
        # float16 latents from the UNet are upcast before entering the decoder.
        if device == "cuda":
            self.pipe.vae.to(dtype=torch.float32)
            _orig_decode = self.pipe.vae.decode

            def _decode_fp32(z, *args, **kwargs):
                return _orig_decode(z.to(dtype=torch.float32), *args, **kwargs)

            self.pipe.vae.decode = _decode_fp32
            print("  VAE upcast to float32 (prevents black-image NaN overflow).")

        print("  Model loaded successfully.")

    def generate(
        self,
        prompt: str,
        width: int = 1024,
        height: int = 1024,
        num_steps: int = 9,
        seed: int = -1,
    ) -> Image.Image:
        import torch
        import numpy as np

        device = _get_device()

        gen_kwargs: dict = {
            "prompt": prompt,
            "height": height,
            "width": width,
            "num_inference_steps": num_steps,
            "guidance_scale": 0.0,  # Turbo variant always uses 0
        }

        if seed >= 0:
            gen_kwargs["generator"] = torch.Generator(device).manual_seed(seed)

        result = self.pipe(**gen_kwargs)
        image = result.images[0]

        if np.array(image).max() == 0:
            import warnings
            warnings.warn(
                "Output image is entirely black — likely NaN/overflow during inference. "
                "Try adding -cpu-offload or reducing image size.",
                RuntimeWarning,
            )

        return image
