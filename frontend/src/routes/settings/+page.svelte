<script lang="ts">
	import Toolbar from '$lib/components/Toolbar.svelte';

	interface Provider {
		id: string;
		name: string;
		type: 'llvm' | 'ollama' | 'gemini';
		enabled: boolean;
		config: {
			apiKey?: string;
			url?: string;
			model?: string;
		};
	}

	let providers: Provider[] = [
		{
			id: '1',
			name: 'LLVM (Default)',
			type: 'llvm',
			enabled: true,
			config: {
				model: 'llvm-default'
			}
		},
		{
			id: '2',
			name: 'Ollama',
			type: 'ollama',
			enabled: false,
			config: {
				url: 'http://localhost:11434',
				model: 'llama2'
			}
		},
		{
			id: '3',
			name: 'Google Gemini',
			type: 'gemini',
			enabled: false,
			config: {
				apiKey: '',
				model: 'gemini-pro'
			}
		}
	];

	let activeTab = 'providers';
	let showApiKey = false;

	function toggleProvider(providerId: string) {
		providers = providers.map(p => 
			p.id === providerId ? { ...p, enabled: !p.enabled } : p
		);
	}

	function updateProviderConfig(providerId: string, field: string, value: string) {
		providers = providers.map(p => 
			p.id === providerId 
				? { ...p, config: { ...p.config, [field]: value } }
				: p
		);
	}

	function saveSettings() {
		// TODO: Implement settings save functionality
		console.log('Saving settings:', providers);
		// Show success message or handle errors
	}

	function resetSettings() {
		// TODO: Implement settings reset functionality
		console.log('Resetting settings');
	}
</script>

<svelte:head>
	<title>Settings - Oracle</title>
	<meta name="description" content="Configure Oracle AI assistant settings and providers" />
</svelte:head>

<div class="min-h-screen  text-white">
	<!-- Header -->
	<header class="fixed top-0 left-0 right-0 z-40 bg-white/5 backdrop-blur-md border-b border-white/10">
		<div class="max-w-4xl mx-auto px-4 py-4">
			<div class="flex items-center justify-between">
				<div class="flex items-center space-x-3">
					<div class="w-8 h-8 bg-gradient-to-br from-blue-400 to-purple-500 rounded-lg flex items-center justify-center">
						<svg class="w-5 h-5 text-white" fill="currentColor" viewBox="0 0 24 24">
							<path d="M19.14,12.94c0.04-0.3,0.06-0.61,0.06-0.94c0-0.32-0.02-0.64-0.07-0.94l2.03-1.58c0.18-0.14,0.23-0.41,0.12-0.61 l-1.92-3.32c-0.12-0.22-0.37-0.29-0.59-0.22l-2.39,0.96c-0.5-0.38-1.03-0.7-1.62-0.94L14.4,2.81c-0.04-0.24-0.24-0.41-0.48-0.41 h-3.84c-0.24,0-0.43,0.17-0.47,0.41L9.25,5.35C8.66,5.59,8.12,5.92,7.63,6.29L5.24,5.33c-0.22-0.08-0.47,0-0.59,0.22L2.74,8.87 C2.62,9.08,2.66,9.34,2.86,9.48l2.03,1.58C4.84,11.36,4.82,11.69,4.82,12s0.02,0.64,0.07,0.94l-2.03,1.58 c-0.18,0.14-0.23,0.41-0.12,0.61l1.92,3.32c0.12,0.22,0.37,0.29,0.59,0.22l2.39-0.96c0.5,0.38,1.03,0.7,1.62,0.94l0.36,2.54 c0.05,0.24,0.24,0.41,0.48,0.41h3.84c0.24,0,0.44-0.17,0.47-0.41l0.36-2.54c0.59-0.24,1.13-0.56,1.62-0.94l2.39,0.96 c0.22,0.08,0.47,0,0.59-0.22l1.92-3.32c0.12-0.22,0.07-0.47-0.12-0.61L19.14,12.94z M12,15.6c-1.98,0-3.6-1.62-3.6-3.6 s1.62-3.6,3.6-3.6s3.6,1.62,3.6,3.6S13.98,15.6,12,15.6z"/>
						</svg>
					</div>
					<div>
						<h1 class="text-xl font-bold bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">Settings</h1>
						<p class="text-xs text-gray-400">Configure Oracle</p>
					</div>
				</div>
			</div>
		</div>
	</header>

	<!-- Main Content -->
	<main class="pt-20 pb-32 px-4">
		<div class="max-w-4xl mx-auto">
			<!-- Tab Navigation -->
			<div class="mb-8">
				<div class="bg-white backdrop-blur-md border border-white rounded-2xl p-2">
					<div class="flex space-x-2">
						<button
							onclick={() => activeTab = 'providers'}
							class="flex-1 py-3 px-4 rounded-xl transition-all duration-300 ease-out hover:bg-white"
							class:bg-white={activeTab === 'providers'}
							class:text-blue-400={activeTab === 'providers'}
							class:text-gray-400={activeTab !== 'providers'}
						>
							<div class="flex items-center justify-center space-x-2">
								<svg class="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
									<path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>
								</svg>
								<span class="font-medium">Providers</span>
							</div>
						</button>
						<button
							onclick={() => activeTab = 'general'}
							class="flex-1 py-3 px-4 rounded-xl transition-all duration-300 ease-out hover:bg-white"
							class:bg-white={activeTab === 'general'}
							class:text-blue-400={activeTab === 'general'}
							class:text-gray-400={activeTab !== 'general'}
						>
							<div class="flex items-center justify-center space-x-2">
								<svg class="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
									<path d="M12 15.5A3.5 3.5 0 0 1 8.5 12A3.5 3.5 0 0 1 12 8.5a3.5 3.5 0 0 1 3.5 3.5 3.5 3.5 0 0 1-3.5 3.5m7.43-2.53c.04-.32.07-.64.07-.97 0-.33-.03-.66-.07-1l2.11-1.63c.19-.15.24-.42.12-.64l-2-3.46c-.12-.22-.39-.31-.61-.22l-2.49 1c-.52-.39-1.06-.73-1.69-.98l-.37-2.65A.506.506 0 0 0 14 2h-4c-.25 0-.46.18-.5.42l-.37 2.65c-.63.25-1.17.59-1.69.98l-2.49-1c-.22-.09-.49 0-.61.22l-2 3.46c-.13.22-.07.49.12.64L4.57 11c-.04.34-.07.67-.07 1 0 .33.03.65.07.97l-2.11 1.66c-.19.15-.25.42-.12.64l2 3.46c.12.22.39.3.61.22l2.49-1.01c.52.4 1.06.74 1.69.99l.37 2.65c.04.24.25.42.5.42h4c.25 0 .46-.18.5-.42l.37-2.65c.63-.26 1.17-.59 1.69-.99l2.49 1.01c.22.08.49 0 .61-.22l2-3.46c.12-.22.07-.49-.12-.64l-2.11-1.66Z"/>
								</svg>
								<span class="font-medium">General</span>
							</div>
						</button>
					</div>
				</div>
			</div>

			<!-- Providers Tab -->
			{#if activeTab === 'providers'}
				<div class="space-y-6">
					{#each providers as provider}
						<div class="bg-white backdrop-blur-md border border-white rounded-2xl p-6 shadow-xl">
							<div class="flex items-center justify-between mb-4">
								<div class="flex items-center space-x-3">
									<div class="w-10 h-10 bg-gradient-to-br from-blue-400 to-purple-500 rounded-lg flex items-center justify-center">
										{#if provider.type === 'llvm'}
											<svg class="w-5 h-5 text-white" fill="currentColor" viewBox="0 0 24 24">
												<path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>
											</svg>
										{:else if provider.type === 'ollama'}
											<svg class="w-5 h-5 text-white" fill="currentColor" viewBox="0 0 24 24">
												<path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
											</svg>
										{:else}
											<svg class="w-5 h-5 text-white" fill="currentColor" viewBox="0 0 24 24">
												<path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>
											</svg>
										{/if}
									</div>
									<div>
										<h3 class="text-lg font-semibold text-white">{provider.name}</h3>
										<p class="text-sm text-gray-400 capitalize">{provider.type} Provider</p>
									</div>
								</div>
								<button
									onclick={() => toggleProvider(provider.id)}
									class="relative inline-flex h-6 w-11 items-center rounded-full transition-colors duration-300"
									class:bg-blue-500={provider.enabled}
									class:bg-gray-600={!provider.enabled}
								>
									<span class="inline-block h-4 w-4 transform rounded-full bg-white transition-transform duration-300"
										class:translate-x-6={provider.enabled}
										class:translate-x-1={!provider.enabled}
									></span>
								</button>
							</div>

							{#if provider.enabled}
								<div class="space-y-4">
									{#if provider.type === 'ollama'}
										<div>
											<label class="block text-sm font-medium text-gray-300 mb-2">Ollama URL</label>
											<input
												type="url"
												bind:value={provider.config.url}
												onchange={(e) => updateProviderConfig(provider.id, 'url', e.target.value)}
												placeholder="http://localhost:11434"
												class="w-full px-4 py-3 bg-white border border-white rounded-xl text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all duration-300"
											/>
										</div>
									{:else if provider.type === 'gemini'}
										<div>
											<label class="block text-sm font-medium text-gray-300 mb-2">API Key</label>
											<div class="relative">
												<input
													type={showApiKey ? 'text' : 'password'}
													bind:value={provider.config.apiKey}
													onchange={(e) => updateProviderConfig(provider.id, 'apiKey', e.target.value)}
													placeholder="Enter your Gemini API key"
													class="w-full px-4 py-3 pr-12 bg-white border border-white rounded-xl text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all duration-300"
												/>
												<button
													onclick={() => showApiKey = !showApiKey}
													class="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-white transition-colors duration-300"
												>
													{#if showApiKey}
														<svg class="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
															<path d="M12 7c2.76 0 5 2.24 5 5 0 .65-.13 1.26-.36 1.83l2.92 2.92c1.51-1.26 2.7-2.89 3.43-4.75-1.73-4.39-6-7.5-11-7.5-1.4 0-2.74.25-3.98.7l2.16 2.16C10.74 7.13 11.35 7 12 7zM2 4.27l2.28 2.28.46.46C3.08 8.3 1.78 10.02 1 12c1.73 4.39 6 7.5 11 7.5 1.55 0 3.03-.3 4.38-.84l.42.42L19.73 22 21 20.73 3.27 3 2 4.27zM7.53 9.8l1.55 1.55c-.05.21-.08.43-.08.65 0 1.66 1.34 3 3 3 .22 0 .44-.03.65-.08l1.55 1.55c-.67.33-1.41.53-2.2.53-2.76 0-5-2.24-5-5 0-.79.2-1.53.53-2.2zm4.31-.78l3.15 3.15.02-.16c0-1.66-1.34-3-3-3l-.17.01z"/>
														</svg>
													{:else}
														<svg class="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
															<path d="M12 4.5C7 4.5 2.73 7.61 1 12c1.73 4.39 6 7.5 11 7.5s9.27-3.11 11-7.5c-1.73-4.39-6-7.5-11-7.5zM12 17c-2.76 0-5-2.24-5-5s2.24-5 5-5 5 2.24 5 5-2.24 5-5 5zm0-8c-1.66 0-3 1.34-3 3s1.34 3 3 3 3-1.34 3-3-1.34-3-3-3z"/>
														</svg>
													{/if}
												</button>
											</div>
										</div>
									{/if}

									<div>
										<label class="block text-sm font-medium text-gray-300 mb-2">Model</label>
										<input
											type="text"
											bind:value={provider.config.model}
											onchange={(e) => updateProviderConfig(provider.id, 'model', e.target.value)}
											placeholder="Enter model name"
											class="w-full px-4 py-3 bg-white border border-white rounded-xl text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all duration-300"
											readonly={provider.type === 'llvm'}
										/>
									</div>
								</div>
							{/if}
						</div>
					{/each}
				</div>
			{/if}

			<!-- General Tab -->
			{#if activeTab === 'general'}
				<div class="bg-white backdrop-blur-md border border-white rounded-2xl p-6 shadow-xl">
					<h3 class="text-lg font-semibold text-white mb-4">General Settings</h3>
					<p class="text-gray-400">General settings will be available in future updates.</p>
				</div>
			{/if}

			<!-- Action Buttons -->
			<div class="mt-8 flex space-x-4">
				<button
					onclick={saveSettings}
					class="flex-1 bg-blue-500 hover:bg-blue-600 text-white font-medium py-3 px-6 rounded-xl transition-all duration-300 ease-out hover:scale-105 active:scale-95"
				>
					Save Settings
				</button>
				<button
					onclick={resetSettings}
					class="flex-1 bg-white hover:bg-white border border-white text-white font-medium py-3 px-6 rounded-xl transition-all duration-300 ease-out hover:scale-105 active:scale-95"
				>
					Reset to Defaults
				</button>
			</div>
		</div>
	</main>

	<!-- Toolbar -->
	<Toolbar />
</div>
