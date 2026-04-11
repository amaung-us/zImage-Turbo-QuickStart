"""
Core image generation logic for Z-Image-Turbo.
"""

import os
from typing import Optional

from PIL import Image


def _get_device():
    """Return the best available device for this machine."""
    import torch
    if torch.backends.mps.is_available():
        return "mps"
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
        # CUDA: float16 is fine.
        # MPS: float16 causes NaN/overflow; bfloat16 has better range.
        # CPU: float32 required.
        if device == "cuda":
            torch_dtype = torch.float16
        elif device == "mps":
            torch_dtype = torch.bfloat16
        else:
            torch_dtype = torch.float32

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
            # MPS generators must be created on "cpu"
            gen_device = "cpu" if device == "mps" else device
            gen_kwargs["generator"] = torch.Generator(gen_device).manual_seed(seed)

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
