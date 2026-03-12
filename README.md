# zImage-Turbo-QuickStart

A simple **QuickStart environment and tooling** for running **Z-Image-Turbo** and its **quantized GGUF** versions with minimal setup.

This project aims to make **Z-Image-Turbo easier to install, run, and experiment with** by providing preconfigured environments, scripts, and setup instructions so anyone can get started quickly.

---
### Overview

**Z-Image-Turbo** is a fast open-source text-to-image model developed by the Tongyi-MAI team at Alibaba. It uses a **6B parameter architecture** and can generate high-quality images in as few as 8 diffusion steps, enabling extremely fast generation while maintaining strong photorealistic quality.

The model is designed to run efficiently on consumer hardware, often fitting within **~16 GB VRAM**, making it accessible for local experimentation and development.

Despite its performance, getting the model running locally—especially with **quantized versions or alternative runtimes**—can require significant setup work.

This repository attempts to **simplify that process**.

---

### Goals

This project focuses on:

- Making **Z-Image-Turbo easier to install and run**
- Providing **ready-to-use environments**
- Supporting **quantized GGUF versions**
- Reducing configuration overhead
- Helping new users get started quickly

In short: **clone → setup → generate images**.

### Current State

- [zImage-Turbo-GGUF](service_zit_gguf.md)
- COMING SOON -- [zImage-Turbo](README.md)
- COMING SOON -- [zImage-Turbo-Container](README.md)

---

### Credits

This repository would not exist without the incredible work of the original developers and contributors.

### Original Model

The **Z-Image-Turbo** model was created by the Tongyi-MAI research team.

- Model repository:
[https://huggingface.co/Tongyi-MAI/Z-Image-Turbo](https://huggingface.co/Tongyi-MAI/Z-Image-Turbo)

Please visit the original repository for:

- official documentation
- research details
- model updates
- licensing information

### GGUF Quantized Models
Quantized **GGUF versions** used in this project were produced by:

- [https://huggingface.co/jayn7/Z-Image-Turbo-GGUF](https://huggingface.co/jayn7/Z-Image-Turbo-GGUF)

These conversions make it easier to run the model with **reduced memory usage and broader runtime compatibility**.