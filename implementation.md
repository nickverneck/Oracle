# VLLM Serving Implementation

## Overview

The backend codebase is designed to support VLLM as an optional, separate service. This separation is achieved through a containerized approach using Docker and Docker Compose.

## Architecture

The key components of the VLLM integration are:

- **`oracle-backend` service**: The main backend application, which runs in its own Docker container. It does not have the `vllm` library installed directly.
- **`oracle-vllm` service**: A dedicated service for VLLM, defined in `docker-compose.yml`. This service is based on the `vllm/vllm-openai:latest` image and is responsible for serving the VLLM model. It is commented out by default, making it optional.
- **Communication**: The `oracle-backend` service communicates with the `oracle-vllm` service via HTTP requests. The `VLLM_BASE_URL` environment variable in the `oracle-backend` service is used to configure the URL of the VLLM service.

## Code-level Implementation

- **`VLLMClient` (`backend/oracle/clients/vllm_client.py`)**: This class implements the client for the VLLM service. It sends requests to the VLLM server using an OpenAI-compatible API.
- **`ModelManager` (`backend/oracle/clients/model_manager.py`)**: This class manages multiple model providers, including VLLM. It has a fallback mechanism that allows it to try other providers if the VLLM service is unavailable.

## How to Enable VLLM

To enable VLLM, the `oracle-vllm` service in the `docker-compose.yml` file needs to be uncommented. This will start the VLLM service in a separate container. The `oracle-backend` service will then be able to communicate with it.

## Dependency Analysis

### VLLM Dependencies

There are no dependencies that need to be removed from the backend's `pyproject.toml` or Dockerfiles. The VLLM dependency is already isolated to the `oracle-vllm` service in the `docker-compose.yml` file.

### PyTorch Dependency

PyTorch is installed in the backend Docker container because it is a dependency of the following libraries:

- **`sentence-transformers`**: Used for generating text embeddings, which are essential for semantic search.
- **`easyocr`**: Used for extracting text from images and scanned PDFs during data ingestion.

The `Dockerfile` is configured to install the CPU-only version of PyTorch to minimize the image size.

## VLLM Client vs. OpenAI Client

A separate `VLLMClient` is necessary because the existing `OpenAIClient` is not compatible with the specific API exposed by the VLLM service. The key differences are:

- **API Endpoint**: `VLLMClient` uses the `/v1/chat/completions` endpoint, while `OpenAIClient` uses the `/completions` endpoint.
- **Payload Structure**: `VLLMClient` sends a `messages` array (for chat models), while `OpenAIClient` sends a `prompt` string (for completion models).
- **Response Parsing**: The clients parse different response structures.

While it would be possible to create a more generic OpenAI-compatible client in the future, the current implementation requires a separate `VLLMClient`.

## Backend Image Size

The backend Docker image is approximately 16GB, which is excessively large. The primary reasons for this are:

- **Large Python Dependencies**: PyTorch, even the CPU-only version, is a large library. Other dependencies of `easyocr` and `sentence-transformers` also contribute to the size.
- **Downloaded Models**: The `easyocr` and `sentence-transformers` libraries download large pre-trained models during the Docker build process. These models are then included in the image, significantly increasing its size.

To address this, a multi-stage Docker build should be implemented. This would involve:

1.  A **build stage** where dependencies are installed and models are downloaded.
2.  A **runtime stage** that copies only the necessary application code, Python environment, and downloaded models from the build stage.

This approach would result in a much smaller final image, as it would not include build-time dependencies or the entire layer history of the model downloads.

## Conclusion

The current implementation already separates the VLLM serving into a different container. VLLM is treated as an optional service, and the backend is designed to handle its availability gracefully. No dependencies need to be removed from the main backend, and the separate `VLLMClient` is necessary for now. The large backend image size is a significant issue that should be addressed by implementing a multi-stage Docker build.