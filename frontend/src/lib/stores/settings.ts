import { writable } from 'svelte/store';
import { browser } from '$app/environment';

export interface Provider {
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

export interface Settings {
	providers: Provider[];
	systemPrompt: string;
	general: {
		theme: 'dark' | 'light';
		language: string;
	};
}

const defaultSettings: Settings = {
	providers: [
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
				model: 'llama3.2'
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
	],
	systemPrompt: 'You are Oracle, a helpful AI assistant. Provide accurate, concise, and helpful responses to user queries.',
	general: {
		theme: 'dark',
		language: 'en'
	}
};

// Load settings from localStorage if available
function loadSettings(): Settings {
	if (!browser) return defaultSettings;
	
	try {
		const stored = localStorage.getItem('oracle-settings');
		if (stored) {
			const parsed = JSON.parse(stored);
			// Merge with defaults to ensure all properties exist
			return {
				...defaultSettings,
				...parsed,
				providers: parsed.providers || defaultSettings.providers,
				general: { ...defaultSettings.general, ...parsed.general }
			};
		}
	} catch (error) {
		console.error('Failed to load settings from localStorage:', error);
	}
	
	return defaultSettings;
}

// Create the store
export const settings = writable<Settings>(loadSettings());

// Save settings to localStorage whenever the store changes
if (browser) {
	settings.subscribe((value) => {
		try {
			localStorage.setItem('oracle-settings', JSON.stringify(value));
		} catch (error) {
			console.error('Failed to save settings to localStorage:', error);
		}
	});
}

// Helper functions for updating settings
export const settingsActions = {
	updateProvider: (providerId: string, updates: Partial<Provider>) => {
		settings.update(current => ({
			...current,
			providers: current.providers.map(p => 
				p.id === providerId ? { ...p, ...updates } : p
			)
		}));
	},
	
	updateProviderConfig: (providerId: string, field: string, value: string) => {
		settings.update(current => ({
			...current,
			providers: current.providers.map(p => 
				p.id === providerId 
					? { ...p, config: { ...p.config, [field]: value } }
					: p
			)
		}));
	},
	
	toggleProvider: (providerId: string) => {
		settings.update(current => ({
			...current,
			providers: current.providers.map(p => 
				p.id === providerId ? { ...p, enabled: !p.enabled } : p
			)
		}));
	},
	
	updateSystemPrompt: (prompt: string) => {
		settings.update(current => ({
			...current,
			systemPrompt: prompt
		}));
	},
	
	updateGeneral: (updates: Partial<Settings['general']>) => {
		settings.update(current => ({
			...current,
			general: { ...current.general, ...updates }
		}));
	},
	
	resetToDefaults: () => {
		settings.set(defaultSettings);
	}
};

// Get the active provider
export function getActiveProvider(currentSettings: Settings): Provider | null {
	return currentSettings.providers.find(p => p.enabled) || null;
}
