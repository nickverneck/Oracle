<script lang="ts">
	import ChatMessage from '$lib/components/ChatMessage.svelte';
	import ChatInput from '$lib/components/ChatInput.svelte';
	import Toolbar from '$lib/components/Toolbar.svelte';
	import { chatService, type ChatMessage as ServiceChatMessage } from '$lib/services/chat';
	import { settings, getActiveProvider } from '$lib/stores/settings';

	interface Message {
		id: string;
		content: string;
		role: 'user' | 'assistant';
		timestamp: Date;
	}

	let messages: Message[] = [
		{
			id: '1',
			content: 'Hello! I\'m Oracle, your AI assistant with knowledge graph and RAG capabilities. How can I help you today?',
			role: 'assistant',
			timestamp: new Date()
		}
	];

	let isLoading = false;
	let chatContainer: HTMLElement;

	function scrollToBottom() {
		if (chatContainer) {
			chatContainer.scrollTop = chatContainer.scrollHeight;
		}
	}

	function generateId(): string {
		return Math.random().toString(36).substr(2, 9);
	}

	async function handleSendMessage(event: CustomEvent<{ message: string }>) {
		const userMessage: Message = {
			id: generateId(),
			content: event.detail.message,
			role: 'user',
			timestamp: new Date()
		};

		messages = [...messages, userMessage];
		isLoading = true;

		// Scroll to bottom after adding user message
		setTimeout(scrollToBottom, 100);

		// Use the chat service to send message to active provider
		try {
			// Convert messages to service format
			const serviceMessages: ServiceChatMessage[] = messages.map(msg => ({
				id: msg.id,
				role: msg.role,
				content: msg.content,
				timestamp: msg.timestamp
			}));

			// Get active provider info for user feedback
			const activeProvider = getActiveProvider($settings);
			const providerName = activeProvider?.name || 'Unknown';

			// Send message using chat service
			const response = await chatService.sendMessage(serviceMessages);

			if (response.success && response.message) {
				const assistantMessage: Message = {
					id: generateId(),
					content: response.message,
					role: 'assistant',
					timestamp: new Date()
				};
				messages = [...messages, assistantMessage];
			} else {
				const errorMessage: Message = {
					id: generateId(),
					content: `Error with ${providerName}: ${response.error || 'Unknown error occurred'}. Please check your provider settings.`,
					role: 'assistant',
					timestamp: new Date()
				};
				messages = [...messages, errorMessage];
			}
		} catch (error) {
			console.error('Error sending message:', error);
			const errorMessage: Message = {
				id: generateId(),
				content: 'Sorry, I encountered an unexpected error. Please try again or check your provider settings.',
				role: 'assistant',
				timestamp: new Date()
			};
			messages = [...messages, errorMessage];
		} finally {
			isLoading = false;
			// Scroll to bottom after adding assistant message
			setTimeout(scrollToBottom, 100);
		}
	}
</script>

<svelte:head>
	<title>Oracle - AI Knowledge Assistant</title>
	<meta name="description" content="Chat with Oracle, your AI assistant powered by knowledge graphs and RAG" />
</svelte:head>

<div class="min-h-screen  text-white">
	<!-- Header -->
	<header class="fixed top-0 left-0 right-0 z-40 bg-white/5 backdrop-blur-md border-b border-white/10">
		<div class="max-w-4xl mx-auto px-4 py-4">
			<div class="flex items-center justify-between">
				<div class="flex items-center space-x-3">
					<div class="w-8 h-8 bg-gradient-to-br from-blue-400 to-purple-500 rounded-lg flex items-center justify-center">
						<svg class="w-5 h-5 text-white" fill="currentColor" viewBox="0 0 24 24">
							<path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
						</svg>
					</div>
					<div>
						<h1 class="text-xl font-bold bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">Oracle</h1>
						<p class="text-xs text-gray-400">AI Knowledge Assistant</p>
					</div>
				</div>
				<div class="flex items-center space-x-2">
					<div class="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
					<span class="text-sm text-gray-400">Online</span>
				</div>
			</div>
		</div>
	</header>

	<!-- Chat Container -->
	<main class="pt-20 pb-40 md:pb-32 px-4">
		<div class="max-w-4xl mx-auto">
			<div 
				bind:this={chatContainer}
				class="h-[calc(89vh-240px)] md:h-[calc(89vh-200px)] overflow-y-auto scrollbar-thin scrollbar-thumb-white/20 scrollbar-track-transparent pr-2 pt-4"
			>
				{#each messages as message (message.id)}
					<ChatMessage {message} />
				{/each}

				{#if isLoading}
					<div class="flex justify-start mb-4">
						<div class="max-w-[80%]">
							<div class="glass rounded-2xl px-4 py-3 shadow-lg">
								<div class="flex items-center space-x-2">
									<div class="flex space-x-1">
										<div class="w-2 h-2 bg-blue-400 rounded-full animate-bounce"></div>
										<div class="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style="animation-delay: 0.1s"></div>
										<div class="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style="animation-delay: 0.2s"></div>
									</div>
									<span class="text-gray-400 text-sm">Oracle is thinking...</span>
								</div>
							</div>
						</div>
					</div>
				{/if}
			</div>
		</div>
	</main>

	<!-- Chat Input -->
	<div class="fixed bottom-24 md:bottom-32 left-0 right-0 px-4 z-30">
		<div class="max-w-4xl mx-auto px-2">
			<ChatInput on:send={handleSendMessage} />
		</div>
	</div>

	<!-- Toolbar -->
	<Toolbar />
</div>
