
export interface UploadedFile {
    id: string;
    name: string;
    size: number;
    type: string;
    status: 'uploading' | 'processing' | 'completed' | 'error';
    progress: number;
    timestamp: Date;
    processingType: 'knowledge-graph' | 'rag' | 'both';
    error?: string;
}

export interface IngestionResponse {
    status: string;
    total_files: number;
    successful_files: number;
    failed_files: number;
    errors: {
        filename: string;
        error_type: string;
        error_message: string;
    }[];
    processing_time: number;
    batch_id?: string;
}

export async function uploadFiles(
    files: File[],
    processingType: 'knowledge-graph' | 'rag' | 'both',
    onUploadProgress: (progress: number) => void
): Promise<IngestionResponse> {
    const formData = new FormData();
    files.forEach(file => {
        formData.append('files', file);
    });

    formData.append('extract_entities', String(processingType === 'knowledge-graph' || processingType === 'both'));
    formData.append('create_embeddings', String(processingType === 'rag' || processingType === 'both'));

    const response = await new Promise<IngestionResponse>((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        xhr.open('POST', '/api/v1/ingest', true);

        xhr.upload.onprogress = (event) => {
            if (event.lengthComputable) {
                const percentComplete = (event.loaded / event.total) * 100;
                onUploadProgress(percentComplete);
            }
        };

        xhr.onload = () => {
            if (xhr.status >= 200 && xhr.status < 300) {
                resolve(JSON.parse(xhr.responseText));
            } else {
                reject(new Error(xhr.statusText));
            }
        };

        xhr.onerror = () => {
            reject(new Error('Network error'));
        };

        xhr.send(formData);
    });

    return response;
}
