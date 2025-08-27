
# Research: Connecting Frontend to Backend for File Ingestion

**Objective:** Implement the functionality to upload documents from the SvelteKit frontend to the FastAPI backend for processing and ingestion into the knowledge base.

## 1. Frontend Analysis (`@frontend/src/routes/data/+page.svelte`)

The current data ingestion UI is a well-structured Svelte component with the following features:

- **File Selection:** Supports both drag-and-drop and a standard file input dialog.
- **File Filtering:** Accepts only files with specific extensions (`.pdf`, `.html`, `.txt`, etc.).
- **Processing Type:** Allows the user to select the processing method ("Knowledge Graph", "RAG", or "Both").
- **UI State:**
    - `files`: An array of `UploadedFile` objects that tracks the state of each file.
    - `dragActive`: A boolean to provide visual feedback when dragging files over the drop zone.
- **Simulated Upload:** The `simulateUpload` function currently mimics the upload and processing flow. This needs to be replaced with actual API calls.

### Key Areas for Modification:

- **`processFiles(fileList: File[])`:** This function is the entry point for handling selected files. It currently adds files to the local state and calls `simulateUpload`.
- **`simulateUpload(fileId: string)`:** This function needs to be replaced with a new function, let's call it `uploadFile`, which will handle the actual file upload to the backend.

## 2. Backend Analysis (`@backend/oracle/api/endpoints/ingest.py`)

The backend provides an ingestion endpoint that is almost ready to be used.

- **Endpoint:** `POST /api/v1/ingest`
- **Request:**
    - `files: List[UploadFile]`: A list of files to be ingested.
    - Form data:
        - `chunk_size: int`
        - `chunk_overlap: int`
        - `extract_entities: bool`
        - `create_embeddings: bool`
        - `language: str`
        - `overwrite_existing: bool`
        - `batch_id: Optional[str]`
- **Response:** `IngestionResponse` model, which includes:
    - `status: str`
    - `total_files: int`
    - `successful_files: int`
    - `failed_files: int`
    - `errors: List[IngestionError]`
    - `processing_time: float`
    - `batch_id: Optional[str]`

The backend is set up to handle multiple file uploads in a single request and provides a detailed response on the outcome.

## 3. Proposed Changes

### Frontend (`@frontend/src/routes/data/+page.svelte`)

1.  **Remove `simulateUpload`:** This function will no longer be needed.
2.  **Implement `uploadFile`:** Create a new `async` function `uploadFile(file: File, uploadedFile: UploadedFile)` that will:
    a. Create a `FormData` object.
    b. Append the file to the `FormData` object.
    c. Append the processing options based on the `processingType` state.
        - If `processingType` is `'knowledge-graph'`, set `extract_entities` to `true` and `create_embeddings` to `false`.
        - If `processingType` is `'rag'`, set `extract_entities` to `false` and `create_embeddings` to `true`.
        - If `processingType` is `'both'`, set `extract_entities` to `true` and `create_embeddings` to `true`.
    d. Use the `fetch` API to send a `POST` request to `/api/v1/ingest`.
    e. Update the file's status in the `files` array based on the API response.
        - On success, change the status to `'completed'`.
        - On failure, change the status to `'error'` and store the error message from the response.

3.  **Update `processFiles`:**
    a. Instead of calling `simulateUpload`, call the new `uploadFile` function for each valid file.
    b. The upload can be done individually for each file or as a batch. The current backend supports batching, so it's more efficient to send all files at once. The `processFiles` function should be modified to collect all files and send them in a single API call.

4.  **Real-time Progress:**
    - The current backend endpoint processes the files and returns a response only after the processing is complete. For real-time progress, we would need to either:
        a. **Polling:** The frontend could poll a `/status/{batch_id}` endpoint. The backend already has this endpoint.
        b. **WebSockets:** For a more advanced solution, the backend could use WebSockets to push status updates to the frontend.
    - For the initial implementation, we can start with a simple "processing" state and then update to "completed" or "error" when the API call finishes.

### Backend (`@backend/oracle/main.py`)

- **CORS Configuration:** Ensure that the FastAPI application is configured to accept requests from the frontend's origin. This is typically done by adding `CORSMiddleware`. I will assume this is already in place from previous tasks.

## 4. File Modifications

- **`@frontend/src/routes/data/+page.svelte`**: This is the main file to be modified on the frontend.
- **`@frontend/src/lib/services/chat.ts`**: It would be good practice to create a new service for ingestion, e.g., `ingestion.ts`, to keep the API calls organized.
- **`@backend/oracle/main.py`**: Potentially needs CORS configuration if not already present.

## 5. UI/UX Enhancements

- **Granular Status:** Instead of a generic "processing" state, the UI could display more specific statuses like "Parsing", "Extracting Entities", "Embedding". This would require the backend to provide more detailed status updates.
- **Error Display:** When a file fails to process, the UI should display the specific error message received from the backend.
- **Upload Progress:** The `fetch` API with `XMLHttpRequest` can be used to track upload progress and update the progress bar in real-time.

By following this plan, we can effectively connect the frontend and backend to create a fully functional file ingestion system.
