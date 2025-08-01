<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import { browser } from '$app/environment';

	const dispatch = createEventDispatcher();

	let message = '';
	let isRecording = false;
	let recognition: SpeechRecognition | null = null;

	// Check if speech recognition is supported
	function isSpeechRecognitionSupported(): boolean {
		if (!browser) return false;
		return 'webkitSpeechRecognition' in window || 'SpeechRecognition' in window;
	}

	function startDictation() {
		if (!browser || !isSpeechRecognitionSupported()) return;
		
		const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
		recognition = new SpeechRecognition();
		recognition.continuous = false;
		recognition.interimResults = true;
		recognition.lang = 'en-US';

		recognition.onstart = () => {
			isRecording = true;
		};

		recognition.onresult = (event: any) => {
			let transcript = '';
			for (let i = event.resultIndex; i < event.results.length; i++) {
				transcript += event.results[i][0].transcript;
			}
			message = transcript;
		};

		recognition.onend = () => {
			isRecording = false;
		};

		recognition.onerror = (event: any) => {
			console.error('Speech recognition error:', event.error);
			isRecording = false;
		};

		recognition.start();
	}

	function stopDictation() {
		if (recognition) {
			recognition.stop();
			isRecording = false;
		}
	}

	function toggleDictation() {
		if (!browser) return;
		if (!isRecording) {
			startDictation();
		} else {
			stopDictation();
		}
	}

	function handleSubmit() {
		if (message.trim()) {
			dispatch('send', { message: message.trim() });
			message = '';
		}
	}

	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Enter' && !event.shiftKey) {
			event.preventDefault();
			handleSubmit();
		}
	}
</script>

<div class="relative">
	<div class="glass rounded-2xl p-4 shadow-xl">
		<div class="flex items-end space-x-3">
			<!-- Text Input -->
			<div class="flex-1 relative">
				<textarea
					bind:value={message}
					onkeydown={handleKeydown}
					placeholder="Ask Oracle anything..."
					class="w-full bg-transparent text-white placeholder-gray-400 resize-none border-none outline-none min-h-[2.5rem] max-h-32 py-2 px-0"
					rows="1"
					style="field-sizing: content;"
				></textarea>
			</div>

			<!-- Send Button -->
			<button
				onclick={handleSubmit}
				disabled={!message.trim()}
				class="p-3 bg-blue-500 hover:bg-blue-600 disabled:bg-gray-600 disabled:cursor-not-allowed rounded-xl transition-all duration-300 ease-out hover:scale-105 active:scale-95"
				aria-label="Send message"
			>
				<svg class="w-5 h-5 text-white" fill="currentColor" viewBox="0 0 24 24">
					<path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
				</svg>
			</button>

			<!-- Dictation Button -->
			<button
				onclick={toggleDictation}
				class="p-3 rounded-xl transition-all duration-300 ease-out hover:scale-105 active:scale-95 {isRecording ? 'bg-red-500 hover:bg-red-600' : 'glass hover:bg-gray-700'}"
				aria-label={isRecording ? 'Stop recording' : 'Start voice input'}
				disabled={!isSpeechRecognitionSupported()}
			>
				{#if isRecording}
					<div class="w-5 h-5 bg-white rounded-full animate-pulse"></div>
				{:else}
					<svg class="w-5 h-5 text-white" fill="currentColor" viewBox="0 0 24 24">
						<path d="M12 14c1.66 0 2.99-1.34 2.99-3L15 5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3zm5.3-3c0 3-2.54 5.1-5.3 5.1S6.7 14 6.7 11H5c0 3.41 2.72 6.23 6 6.72V21h2v-3.28c3.28-.48 6-3.3 6-6.72h-1.7z"/>
					</svg>
				{/if}
			</button>
		</div>

		<!-- Recording Indicator -->
		{#if isRecording}
			<div class="mt-2 flex items-center justify-center">
				<div class="flex items-center space-x-2 text-red-400">
					<div class="w-2 h-2 bg-red-400 rounded-full animate-pulse"></div>
					<span class="text-sm">Listening...</span>
				</div>
			</div>
		{/if}
	</div>
</div>
