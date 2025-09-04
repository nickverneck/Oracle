# OpenAI-Compatible Provider Implementation Plan

This document outlines the plan to add support for OpenAI-compatible APIs (like LM Studio) to the frontend, ensuring that these requests are routed through the backend to leverage the RAG pipeline.

## 1. Update the Settings Store

File: `frontend/src/lib/stores/settings.ts`

- **Add a new provider type:** The `Provider` type definition will be updated to include `'openai'` as a possible value for the `type` property.
- **Add a new default provider:** A new provider configuration for "OpenAI Compatible" will be added to the `defaultSettings` object. This will include:
  - `id`: A unique identifier (e.g., `'openai-compatible'`).
  - `name`: `'OpenAI Compatible'`.
  - `type`: `'openai'`.
  - `enabled`: `false`.
  - `config`: An object with `url` and `apiKey` fields, both initially empty.

## 2. Update the Settings UI

File: `frontend/src/routes/settings/+page.svelte`

- **Create a new UI section:** A new `{:else if provider.type === 'openai'}` block will be added to the UI to render the settings for the new provider type.
- **Input Fields:** This section will contain two input fields:
  - **API URL:** A text input for the user to enter the URL of their OpenAI-compatible API.
  - **API Key:** A password input for the API key, with a show/hide toggle button for better user experience, similar to the existing Gemini API key field.

## 3. Update the Chat Service

File: `frontend/src/lib/services/chat.ts`

- **Create `sendToBackend` function:** A new private async function `sendToBackend` will be created. This function will be responsible for sending chat messages to the backend's `/api/v1/chat` endpoint.
- **Modify `sendMessage` function:** The main `sendMessage` function will be updated to handle the new `'openai'` provider type. A `switch` statement will be used to determine which function to call based on the active provider's type.
  - If the provider is `'openai'`, `sendToBackend` will be called.
  - The existing `sendToOllama` and `sendToGemini` functions will remain for direct-to-LLM communication.
- **`sendToBackend` Implementation:** This function will accept the `messages` array and the active provider's configuration. It will then make a `POST` request to the backend's `/api/v1/chat` endpoint, sending a JSON payload containing the messages and the provider configuration.

## 4. Update the Backend Chat Endpoint

File: `backend/oracle/api/endpoints/chat.py` and related files.

- **Review and Update `ChatRequest` model:** The `ChatRequest` model in `backend/oracle/models/chat.py` will be reviewed and updated to include the provider configuration sent from the frontend.
- **Update `ChatService`:** The `ChatService` in `backend/oracle/services/conversation.py` will be modified to handle the new `'openai'` provider type. It will use the provider configuration from the request to make the final call to the specified OpenAI-compatible LLM *after* the RAG pipeline has been executed.
- **Dynamic LLM Client:** The backend will need a mechanism to dynamically instantiate a client for the OpenAI-compatible API based on the provided URL and API key. This might involve creating a new client class similar to the existing `GeminiClient` or `OllamaClient`.
