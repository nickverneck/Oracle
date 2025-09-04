# Project Tasks

This file outlines the tasks required to improve the Docker build process, refactor the model clients, and add support for CUDA.

## 1. Separate VLLM Service

- [ ] Uncomment the `oracle-vllm` service in the `docker-compose.yml` file to enable VLLM for local development and production.
- [ ] Ensure the `VLLM_BASE_URL` environment variable in the `oracle-backend` service is correctly configured to point to the `oracle-vllm` service.

## 2. Refactor Model Clients

- [ ] Create a generic OpenAI-compatible client that can handle both chat and completion endpoints.
- [ ] Update the `VLLMClient` and `OpenAIClient` to use the new generic client, configured with the appropriate parameters for each service.
- [ ] Update the `ModelManager` to use the refactored clients.

## 3. Optimize Docker Build Process

- [ ] Implement a multi-stage `Dockerfile` for the `oracle-backend` service to reduce the final image size.
- [ ] **Build Stage**:
    - Install build-time dependencies, including `build-essential`.
    - Install Python dependencies using `uv`.
    - Add a step to pre-download the models for `sentence-transformers` and `easyocr` to prevent them from being downloaded at runtime.
- [ ] **Runtime Stage**:
    - Copy the application code, Python environment, and pre-downloaded models from the build stage.
    - Install only the necessary runtime system dependencies.

## 4. Add CUDA Support

- [x] Modify the `Dockerfile` to support CUDA for GPU acceleration.
- [x] Use a `CUDA_ENABLED` environment variable in the `.env` file to control whether to build the image with CUDA support.
- [x] If `CUDA_ENABLED` is true, install a version of PyTorch with CUDA 11.8 support, which is compatible with the NVIDIA 1080 Ti.
- [x] If `CUDA_ENABLED` is false or not set, install the CPU-only version of PyTorch.
- [x] Update the `docker-compose.yml` file to pass the `CUDA_ENABLED` build argument to the `oracle-backend` service.
