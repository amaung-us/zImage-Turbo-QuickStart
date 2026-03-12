## Z-Image-Turbo

[Back to index](index.md)

- [Download](#download-zimage-turbo)
- [Local Run (Z-Image-Turbo)](#local-Universal)
- [Local Run (Z-Image-Turbo GGUF)](service_zit_gguf.md)
---
# Download ZImage-Turbo


Download Z-Image-Turbo from one of the followings
<br>
*(remember Z-Image-Turbo != Z-Image)*

```
[Original]
https://huggingface.co/Tongyi-MAI/Z-Image-Turbo

[GGUF Quantized]
https://huggingface.co/jayn7/Z-Image-Turbo-GGUF



hf download <repo_id> --local-dir <path_to_folder>
```
---
# Local Universal
Download [Setup-Script](assets/setup-zimage-universal.sh) and [Local Text2Image](assets/zimage_t2i.py) script 

These two scripts are made for Universal Solutions. Setup can be used get the system going to make sure all the needed libraries and environments are setup correctly on
 - MacOS
 - Linux (NVidia)
 - Linux (RocM)


areas to edit and how to run setup-zimage-universal.sh
```bash
# -----------------------
# Make sure to point to the right venv
# Make a new venv with Python -m venv <location>
# -----------------------
VENV_DIR="$HOME/venvs/zimage"

# -----------------------
# run ./setup-zimage-universal.sh with 
# example:
# ./setup-zimage-universal.sh -mps (for running on MacOS)
# -----------------------
Nvidia GPU options:
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
```
---

# Local GGUF
Create python environment if it does not exist
```bash
python3 -m venv <location>
```
From the environment, create a zit-gguf_t2i.py as shown below and run with **python3 zit-gguf_t2i.py:
```python
import torch
from diffusers import ZImagePipeline, ZImageTransformer2DModel, GGUFQuantizationConfig

print("torch:", torch.__version__)
print("cuda available:", torch.cuda.is_available())
if torch.cuda.is_available():
    print("gpu:", torch.cuda.get_device_name(0))

prompt = "A cinematic portrait of a woman sitting at a table in restaurant at night"

height = 512
width = 512
seed = 42

dtype = torch.bfloat16
local_path = "/srv/models/z-image-turbo/z_image_turbo-Q3_K_S.gguf"

transformer = ZImageTransformer2DModel.from_single_file(
    local_path,
    quantization_config=GGUFQuantizationConfig(compute_dtype=dtype),
    dtype=dtype,
)

pipe = ZImagePipeline.from_pretrained(
    "Tongyi-MAI/Z-Image-Turbo",
    transformer=transformer,
    torch_dtype=dtype,
)

pipe.enable_model_cpu_offload()

image = pipe(
    prompt=prompt,
    num_inference_steps=9,
    guidance_scale=0.0,
    height=height,
    width=width,
    generator=torch.Generator(device="cuda").manual_seed(seed),
).images[0]

image.save("zimage_q3ks_bf16_512.png")
print("saved zimage_q3ks_bf16_512.png")
```