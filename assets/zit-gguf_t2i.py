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
local_path = "/srv/models/z-image-turbo/gguf/z_image_turbo-Q3_K_S.gguf"

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