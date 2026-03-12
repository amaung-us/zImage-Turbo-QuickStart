import os
import time
import uuid
from pathlib import Path

import gradio as gr
import torch
from diffusers import ZImagePipeline, ZImageTransformer2DModel, GGUFQuantizationConfig

# ----------------------------
# Configuration
# ----------------------------

MODEL_PATHS = {
    "Q3_K_S": "/srv/models/z-image-turbo/z_image_turbo-Q3_K_S.gguf",
    "Q4_K_S": "/srv/models/z-image-turbo/z_image_turbo-Q4_K_S.gguf",
    "Q4_K_M": "/srv/models/z-image-turbo/z_image_turbo-Q4_K_M.gguf",
}

BASE_MODEL_ID = "Tongyi-MAI/Z-Image-Turbo"

OUTPUT_DIR = Path("./outputs")
OUTPUT_DIR.mkdir(exist_ok=True)

DEFAULT_MODEL = "Q3_K_S"
DEFAULT_DTYPE = "bfloat16"


# ----------------------------
# Utilities
# ----------------------------

def torch_dtype(name):
    return {
        "float16": torch.float16,
        "bfloat16": torch.bfloat16,
        "float32": torch.float32,
    }[name]


def gpu_status():
    if not torch.cuda.is_available():
        return "CUDA not available"

    props = torch.cuda.get_device_properties(0)
    total = props.total_memory / 1024**3
    alloc = torch.cuda.memory_allocated(0) / 1024**3

    return f"{torch.cuda.get_device_name(0)} | VRAM {alloc:.2f}/{total:.1f} GB"


PIPELINES = {}



# ----------------------------
# Load pipeline
# ----------------------------

def get_pipeline(model_name, dtype_name, cpu_offload):

    key = (model_name, dtype_name, cpu_offload)

    if key in PIPELINES:
        return PIPELINES[key]

    dtype = torch_dtype(dtype_name)

    model_path = MODEL_PATHS[model_name]

    transformer = ZImageTransformer2DModel.from_single_file(
        model_path,
        quantization_config=GGUFQuantizationConfig(compute_dtype=dtype),
        dtype=dtype,
    )

    pipe = ZImagePipeline.from_pretrained(
        BASE_MODEL_ID,
        transformer=transformer,
        torch_dtype=dtype,
    )

    if cpu_offload:
        pipe.enable_model_cpu_offload()
    else:
        pipe = pipe.to("cuda")

    PIPELINES[key] = pipe

    return pipe



# ----------------------------
# Generate Image
# ----------------------------

def generate(
    prompt,
    negative_prompt,
    model_name,
    dtype_name,
    width,
    height,
    steps,
    guidance,
    seed,
    cpu_offload,
):

    pipe = get_pipeline(model_name, dtype_name, cpu_offload)

    generator = torch.Generator("cuda").manual_seed(int(seed))

    image = pipe(
        prompt=prompt,
        negative_prompt=negative_prompt if negative_prompt else None,
        num_inference_steps=int(steps),
        guidance_scale=float(guidance),
        width=int(width),
        height=int(height),
        generator=generator,
    ).images[0]

    filename = OUTPUT_DIR / f"zimage_{uuid.uuid4().hex[:8]}.png"
    image.save(filename)

    return image, str(filename)



# ----------------------------
# Web UI
# ----------------------------

with gr.Blocks(title="Z-Image Turbo") as demo:

    gr.Markdown("# Z-Image Turbo")
    gr.Markdown("Local image generation UI")

    gpu_box = gr.Textbox(label="GPU Status", value=gpu_status(), interactive=False)

    with gr.Row():

        with gr.Column(scale=2):

            prompt = gr.Textbox(
                label="Prompt",
                lines=6,
                value="A cinematic portrait of a woman in traditional red Hanfu at night"
            )

            negative_prompt = gr.Textbox(
                label="Negative Prompt",
                lines=2,
                value="blurry, low quality, distorted"
            )

            with gr.Row():

                model = gr.Dropdown(
                    MODEL_PATHS.keys(),
                    value=DEFAULT_MODEL,
                    label="GGUF Model"
                )

                dtype = gr.Dropdown(
                    ["bfloat16", "float16", "float32"],
                    value=DEFAULT_DTYPE,
                    label="Compute Dtype"
                )

                cpu_offload = gr.Checkbox(
                    True,
                    label="CPU Offload"
                )

            with gr.Row():

                width = gr.Dropdown([512, 768, 1024], value=512, label="Width")
                height = gr.Dropdown([512, 768, 1024], value=512, label="Height")

                steps = gr.Slider(1, 20, value=9, step=1, label="Steps")

            with gr.Row():

                guidance = gr.Slider(0, 7.5, value=0, step=0.1, label="Guidance")
                seed = gr.Number(value=42, label="Seed")

            generate_btn = gr.Button("Generate")

        with gr.Column(scale=3):

            image_out = gr.Image(label="Generated Image")
            saved_path = gr.Textbox(label="Saved File", interactive=False)

    generate_btn.click(
        fn=generate,
        inputs=[
            prompt,
            negative_prompt,
            model,
            dtype,
            width,
            height,
            steps,
            guidance,
            seed,
            cpu_offload
        ],
        outputs=[image_out, saved_path],
    ).then(
        fn=lambda: gpu_status(),
        outputs=gpu_box
    )


# ----------------------------
# Run server
# ----------------------------

if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860
    )

