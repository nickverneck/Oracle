<script lang="ts">
	import Toolbar from '$lib/components/Toolbar.svelte';

	interface UploadedFile {
		id: string;
		name: string;
		size: number;
		type: string;
		status: 'uploading' | 'processing' | 'completed' | 'error';
		progress: number;
		timestamp: Date;
		processingType: 'knowledge-graph' | 'rag' | 'both';
	}

	let files: UploadedFile[] = [];
	let dragActive = false;
	let processingType: 'knowledge-graph' | 'rag' | 'both' = 'both';
	let fileInput: HTMLInputElement;

	const acceptedTypes = [
		'.pdf',
		'.html',
		'.htm',
		'.txt',
		'.md',
		'.markdown',
		'.doc',
		'.docx'
	];

	function generateId(): string {
		return Math.random().toString(36).substr(2, 9);
	}

	function formatFileSize(bytes: number): string {
		if (bytes === 0) return '0 Bytes';
		const k = 1024;
		const sizes = ['Bytes', 'KB', 'MB', 'GB'];
		const i = Math.floor(Math.log(bytes) / Math.log(k));
		return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
	}

	function handleDragEnter(e: DragEvent) {
		e.preventDefault();
		dragActive = true;
	}

	function handleDragLeave(e: DragEvent) {
		e.preventDefault();
		dragActive = false;
	}

	function handleDragOver(e: DragEvent) {
		e.preventDefault();
	}

	function handleDrop(e: DragEvent) {
		e.preventDefault();
		dragActive = false;
		
		const droppedFiles = Array.from(e.dataTransfer?.files || []);
		processFiles(droppedFiles);
	}

	function handleFileSelect(e: Event) {
		const target = e.target as HTMLInputElement;
		const selectedFiles = Array.from(target.files || []);
		processFiles(selectedFiles);
		target.value = ''; // Reset input
	}

	function processFiles(fileList: File[]) {
		const validFiles = fileList.filter(file => {
			const extension = '.' + file.name.split('.').pop()?.toLowerCase();
			return acceptedTypes.includes(extension);
		});

		validFiles.forEach(file => {
			const uploadedFile: UploadedFile = {
				id: generateId(),
				name: file.name,
				size: file.size,
				type: file.type || 'application/octet-stream',
				status: 'uploading',
				progress: 0,
				timestamp: new Date(),
				processingType
			};

			files = [...files, uploadedFile];
			simulateUpload(uploadedFile.id);
		});
	}

	async function simulateUpload(fileId: string) {
		// Simulate upload progress
		for (let progress = 0; progress <= 100; progress += 10) {
			await new Promise(resolve => setTimeout(resolve, 200));
			files = files.map(f => 
				f.id === fileId ? { ...f, progress } : f
			);
		}

		// Change to processing
		files = files.map(f => 
			f.id === fileId ? { ...f, status: 'processing', progress: 0 } : f
		);

		// Simulate processing
		for (let progress = 0; progress <= 100; progress += 5) {
			await new Promise(resolve => setTimeout(resolve, 300));
			files = files.map(f => 
				f.id === fileId ? { ...f, progress } : f
			);
		}

		// Complete
		files = files.map(f => 
			f.id === fileId ? { ...f, status: 'completed', progress: 100 } : f
		);
	}

	function removeFile(fileId: string) {
		files = files.filter(f => f.id !== fileId);
	}

	function retryFile(fileId: string) {
		files = files.map(f => 
			f.id === fileId ? { ...f, status: 'uploading', progress: 0 } : f
		);
		simulateUpload(fileId);
	}

	function clearCompleted() {
		files = files.filter(f => f.status !== 'completed');
	}

	function openFileDialog() {
		fileInput?.click();
	}
</script>

<svelte:head>
	<title>Data Ingestion - Oracle</title>
	<meta name="description" content="Upload and process documents for Oracle AI knowledge base" />
</svelte:head>

<div class="min-h-screen  text-white">
	<!-- Header -->
	<header class="fixed top-0 left-0 right-0 z-40 bg-white/5 backdrop-blur-md border-b border-white/10">
		<div class="max-w-4xl mx-auto px-4 py-4">
			<div class="flex items-center justify-between">
				<div class="flex items-center space-x-3">
					<div class="w-8 h-8 bg-gradient-to-br from-blue-400 to-purple-500 rounded-lg flex items-center justify-center">
						<svg class="w-5 h-5 text-white" fill="currentColor" viewBox="0 0 24 24">
							<path d="M14,2H6A2,2 0 0,0 4,4V20A2,2 0 0,0 6,22H18A2,2 0 0,0 20,20V8L14,2M18,20H6V4H13V9H18V20Z"/>
						</svg>
					</div>
					<div>
						<h1 class="text-xl font-bold bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">Data Ingestion</h1>
						<p class="text-xs text-gray-400">Upload & Process Documents</p>
					</div>
				</div>
			</div>
		</div>
	</header>

	<!-- Main Content -->
	<main class="pt-20 pb-32 px-4">
		<div class="max-w-4xl mx-auto">
			<!-- Processing Type Selection -->
			<div class="mt-6 glass rounded-2xl p-6 shadow-xl">
				<h3 class="text-lg font-semibold text-white mb-4">Processing Method</h3>
				<div class="grid grid-cols-1 md:grid-cols-3 gap-4">
					<button
						onclick={() => processingType = 'knowledge-graph'}
						class="p-4 rounded-xl border-2 transition-all duration-300 ease-out hover:scale-105 active:scale-95 {processingType === 'knowledge-graph' ? 'border-blue-500 bg-blue-500' : 'border-white bg-white/5'}"
					>
						<div class="flex flex-col items-center space-y-2">
							<svg class="w-8 h-8 text-blue-400" fill="currentColor" viewBox="0 0 24 24">
								<path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>
							</svg>
							<span class="font-medium">Knowledge Graph</span>
							<p class="text-xs text-gray-400 text-center">Extract entities and relationships</p>
						</div>
					</button>
					<button
						onclick={() => processingType = 'rag'}
						class="p-4 rounded-xl border-2 transition-all duration-300 ease-out hover:scale-105 active:scale-95 {processingType === 'rag' ? 'border-blue-500 bg-blue-500' : 'border-white bg-white/5'}"
					>
						<div class="flex flex-col items-center space-y-2">
							<svg class="w-8 h-8 text-purple-400" fill="currentColor" viewBox="0 0 24 24">
								<path d="M9 3V18H12V3H9M12 5L16 18L19 17L15 4L12 5Z"/>
							</svg>
							<span class="font-medium">RAG</span>
							<p class="text-xs text-gray-400 text-center">Retrieval augmented generation</p>
						</div>
					</button>
					<button
						onclick={() => processingType = 'both'}
						class="p-4 rounded-xl border-2 transition-all duration-300 ease-out hover:scale-105 active:scale-95 {processingType === 'both' ? 'border-blue-500 bg-blue-500' : 'border-gray-600 bg-gray-800 bg-opacity-20'}"
					>
						<div class="flex flex-col items-center space-y-2">
							<svg class="w-8 h-8 text-green-400" fill="currentColor" viewBox="0 0 24 24">
								<path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
							</svg>
							<span class="font-medium">Both</span>
							<p class="text-xs text-gray-400 text-center">Knowledge graph + RAG</p>
						</div>
					</button>
				</div>
			</div>

			<!-- File Upload Area -->
			<div class="mb-8 mt-6">
				<div
					class="relative glass border-2 border-dashed rounded-2xl p-12 text-center transition-all duration-300 ease-out"
					class:border-blue-500={dragActive}
					class:bg-blue-500={dragActive}
					class:border-gray-600={!dragActive}
					ondragenter={handleDragEnter}
					ondragleave={handleDragLeave}
					ondragover={handleDragOver}
					ondrop={handleDrop}
				>
					<div class="flex flex-col items-center space-y-4">
						<div class="w-16 h-16 bg-gradient-to-br from-blue-400 to-purple-500 rounded-2xl flex items-center justify-center">
							<svg class="w-8 h-8 text-white" fill="currentColor" viewBox="0 0 24 24">
								<path d="M14,2H6A2,2 0 0,0 4,4V20A2,2 0 0,0 6,22H18A2,2 0 0,0 20,20V8L14,2M18,20H6V4H13V9H18V20Z"/>
							</svg>
						</div>
						<div>
							<h3 class="text-xl font-semibold text-white mb-2">
								{dragActive ? 'Drop files here' : 'Upload Documents'}
							</h3>
							<p class="text-gray-400 mb-4">
								Drag and drop files here, or click to browse
							</p>
							<p class="text-sm text-gray-500">
								Supported: PDF, HTML, TXT, Markdown, DOC, DOCX
							</p>
						</div>
						<button
							onclick={openFileDialog}
							class="bg-blue-500 hover:bg-blue-600 text-white font-medium py-3 px-6 rounded-xl transition-all duration-300 ease-out hover:scale-105 active:scale-95"
						>
							Choose Files
						</button>
					</div>
				</div>
			</div>

			<!-- File List -->
			{#if files.length > 0}
				<div class="bg-white backdrop-blur-md border border-white rounded-2xl p-6 shadow-xl">
					<div class="flex items-center justify-between mb-6">
						<h3 class="text-lg font-semibold text-white">Uploaded Files ({files.length})</h3>
						<button
							onclick={clearCompleted}
							class="text-sm text-gray-400 hover:text-white transition-colors duration-300"
						>
							Clear Completed
						</button>
					</div>

					<div class="space-y-4">
						{#each files as file}
							<div class="bg-white/5 border border-white/10 rounded-xl p-4">
								<div class="flex items-center justify-between mb-2">
									<div class="flex items-center space-x-3">
										<div class="w-10 h-10 bg-gradient-to-br from-blue-400 to-purple-500 rounded-lg flex items-center justify-center">
											<svg class="w-5 h-5 text-white" fill="currentColor" viewBox="0 0 24 24">
												<path d="M14,2H6A2,2 0 0,0 4,4V20A2,2 0 0,0 6,22H18A2,2 0 0,0 20,20V8L14,2M18,20H6V4H13V9H18V20Z"/>
											</svg>
										</div>
										<div>
											<h4 class="font-medium text-white">{file.name}</h4>
											<p class="text-sm text-gray-400">{formatFileSize(file.size)} • {file.processingType}</p>
										</div>
									</div>
									<div class="flex items-center space-x-2">
										{#if file.status === 'completed'}
											<div class="w-6 h-6 bg-green-500 rounded-full flex items-center justify-center">
												<svg class="w-4 h-4 text-white" fill="currentColor" viewBox="0 0 24 24">
													<path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/>
												</svg>
											</div>
										{:else if file.status === 'error'}
											<button
												onclick={() => retryFile(file.id)}
												class="w-6 h-6 bg-red-500 rounded-full flex items-center justify-center hover:bg-red-600 transition-colors duration-300"
											>
												<svg class="w-4 h-4 text-white" fill="currentColor" viewBox="0 0 24 24">
													<path d="M17.65,6.35C16.2,4.9 14.21,4 12,4A8,8 0 0,0 4,12A8,8 0 0,0 12,20C15.73,20 18.84,17.45 19.73,14H17.65C16.83,16.33 14.61,18 12,18A6,6 0 0,1 6,12A6,6 0 0,1 12,6C13.66,6 15.14,6.69 16.22,7.78L13,11H20V4L17.65,6.35Z"/>
												</svg>
											</button>
										{:else}
											<div class="w-6 h-6 bg-blue-500 rounded-full flex items-center justify-center animate-spin">
												<svg class="w-4 h-4 text-white" fill="currentColor" viewBox="0 0 24 24">
													<path d="M12,4V2A10,10 0 0,0 2,12H4A8,8 0 0,1 12,4Z"/>
												</svg>
											</div>
										{/if}
										<button
											onclick={() => removeFile(file.id)}
											class="w-6 h-6 text-gray-400 hover:text-red-400 transition-colors duration-300"
										>
											<svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
												<path d="M19,6.41L17.59,5L12,10.59L6.41,5L5,6.41L10.59,12L5,17.59L6.41,19L12,13.41L17.59,19L19,17.59L13.41,12L19,6.41Z"/>
											</svg>
										</button>
									</div>
								</div>

								{#if file.status !== 'completed' && file.status !== 'error'}
									<div class="w-full bg-white rounded-full h-2">
										<div 
											class="bg-blue-500 h-2 rounded-full transition-all duration-300"
											style="width: {file.progress}%"
										></div>
									</div>
									<p class="text-xs text-gray-400 mt-1">
										{file.status === 'uploading' ? 'Uploading' : 'Processing'}: {file.progress}%
									</p>
								{/if}
							</div>
						{/each}
					</div>
				</div>
			{/if}
		</div>
	</main>

	<!-- Hidden File Input -->
	<input
		bind:this={fileInput}
		type="file"
		multiple
		accept={acceptedTypes.join(',')}
		onchange={handleFileSelect}
		class="hidden"
	/>

	<!-- Toolbar -->
	<Toolbar />
</div>
