import { get } from 'svelte/store';
import { settings, getActiveProvider, type Provider } from '$lib/stores/settings';

export interface ChatMessage {
	id: string;
	role: 'user' | 'assistant';
	content: string;
	timestamp: Date;
}

export interface ChatResponse {
	success: boolean;
	message?: string;
	error?: string;
}

class ChatService {
	private async sendToOllama(provider: Provider, messages: ChatMessage[]): Promise<ChatResponse> {
		try {
			const { url, model } = provider.config;
			if (!url || !model) {
				return { success: false, error: 'Ollama URL or model not configured' };
			}

			// Get current settings for system prompt
			const currentSettings = get(settings);
			
			// Format messages for Ollama API
			const formattedMessages = [
				{
					role: 'system',
					content: currentSettings.systemPrompt
				},
				...messages.map(msg => ({
					role: msg.role,
					content: msg.content
				}))
			];

			const response = await fetch(`${url}/api/chat`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
				},
				body: JSON.stringify({
					model: model,
					messages: formattedMessages,
					stream: false
				})
			});

			if (!response.ok) {
				throw new Error(`Ollama API error: ${response.status} ${response.statusText}`);
			}

			const data = await response.json();
			
			if (data.message && data.message.content) {
				return {
					success: true,
					message: data.message.content
				};
			} else {
				return {
					success: false,
					error: 'Invalid response format from Ollama'
				};
			}
		} catch (error) {
			console.error('Ollama API error:', error);
			return {
				success: false,
				error: error instanceof Error ? error.message : 'Unknown error occurred'
			};
		}
	}

	private async sendToGemini(provider: Provider, messages: ChatMessage[]): Promise<ChatResponse> {
		try {
			const { apiKey, model } = provider.config;
			if (!apiKey || !model) {
				return { success: false, error: 'Gemini API key or model not configured' };
			}

			// Get current settings for system prompt
			const currentSettings = get(settings);
			
			// Format the conversation for Gemini
			const prompt = `${currentSettings.systemPrompt}\n\nConversation:\n${messages.map(msg => 
				`${msg.role === 'user' ? 'User' : 'Assistant'}: ${msg.content}`
			).join('\n')}\n\nAssistant:`;

			const response = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${apiKey}`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
				},
				body: JSON.stringify({
					contents: [{
						parts: [{
							text: prompt
						}]
					}]
				})
			});

			if (!response.ok) {
				throw new Error(`Gemini API error: ${response.status} ${response.statusText}`);
			}

			const data = await response.json();
			
			if (data.candidates && data.candidates[0] && data.candidates[0].content && data.candidates[0].content.parts[0]) {
				return {
					success: true,
					message: data.candidates[0].content.parts[0].text
				};
			} else {
				return {
					success: false,
					error: 'Invalid response format from Gemini'
				};
			}
		} catch (error) {
			console.error('Gemini API error:', error);
			return {
				success: false,
				error: error instanceof Error ? error.message : 'Unknown error occurred'
			};
		}
	}

	private async sendToLLVM(provider: Provider, messages: ChatMessage[]): Promise<ChatResponse> {
		// Placeholder for LLVM integration
		// For now, return a mock response
		const currentSettings = get(settings);
		
		return {
			success: true,
			message: `This is a mock response from LLVM. System prompt: "${currentSettings.systemPrompt}". Last message: "${messages[messages.length - 1]?.content || 'No message'}"`
		};
	}

	async sendMessage(messages: ChatMessage[]): Promise<ChatResponse> {
		const currentSettings = get(settings);
		const activeProvider = getActiveProvider(currentSettings);

		if (!activeProvider) {
			return {
				success: false,
				error: 'No active provider configured. Please enable a provider in settings.'
			};
		}

		switch (activeProvider.type) {
			case 'openai':
				return this.sendToBackend(activeProvider, messages);
			case 'ollama':
				return this.sendToOllama(activeProvider, messages);
			case 'gemini':
				return this.sendToGemini(activeProvider, messages);
			case 'llvm':
				return this.sendToLLVM(activeProvider, messages);
			default:
				return {
					success: false,
					error: `Unsupported provider type: ${activeProvider.type}`
				};
		}
	}

	async testConnection(provider: Provider): Promise<ChatResponse> {
		switch (provider.type) {
			case 'ollama':
				try {
					const { url } = provider.config;
					if (!url) {
						return { success: false, error: 'Ollama URL not configured' };
					}

					const response = await fetch(`${url}/api/tags`);
					if (response.ok) {
						return { success: true, message: 'Ollama connection successful' };
					} else {
						return { success: false, error: `Connection failed: ${response.status}` };
					}
				} catch (error) {
					return { success: false, error: 'Failed to connect to Ollama' };
				}
			
			case 'gemini':
				// Test with a simple request
				return this.sendToGemini(provider, [{
					id: 'test',
					role: 'user',
					content: 'Hello',
					timestamp: new Date()
				}]);
			
			case 'llvm':
				return { success: true, message: 'LLVM is always available' };
			
			default:
				return { success: false, error: 'Unknown provider type' };
		}
	}
}

export const chatService = new ChatService();
