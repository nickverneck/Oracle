<script lang="ts">
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	
	// Icons for navigation
	const navigationItems = [
		{ path: '/', icon: 'chat', label: 'Chat', ariaLabel: 'Go to chat' },
		{ path: '/settings', icon: 'settings', label: 'Settings', ariaLabel: 'Go to settings' },
		{ path: '/data', icon: 'upload', label: 'Data', ariaLabel: 'Go to data ingestion' }
	];

	function isActive(path: string): boolean {
		return $page.url.pathname === path;
	}

	function navigate(path: string) {
		goto(path);
	}
</script>

<!-- Desktop Toolbar -->
<nav class="fixed bottom-6 left-1/2 transform -translate-x-1/2 z-50 hidden md:block">
	<div class="glass rounded-2xl px-6 py-3 shadow-xl">
		<div class="flex items-center space-x-8">
			{#each navigationItems as item}
				<button
					onclick={() => navigate(item.path)}
					class="group relative flex flex-col items-center space-y-1 px-4 py-2 rounded-xl transition-all duration-300 ease-out hover:bg-gray-700 hover:scale-105 active:scale-95"
					class:active={isActive(item.path)}
					aria-label={item.ariaLabel}
				>
					<div class="relative">
						{#if item.icon === 'chat'}
							<svg class="w-6 h-6 transition-colors duration-300" class:text-blue-400={isActive(item.path)} class:text-gray-400={!isActive(item.path)} fill="currentColor" viewBox="0 0 24 24">
								<path d="M20 2H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h4l4 4 4-4h4c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm-2 12H6v-2h12v2zm0-3H6V9h12v2zm0-3H6V6h12v2z"/>
							</svg>
						{:else if item.icon === 'settings'}
							<svg class="w-6 h-6 transition-colors duration-300" class:text-blue-400={isActive(item.path)} class:text-gray-400={!isActive(item.path)} fill="currentColor" viewBox="0 0 24 24">
								<path d="M19.14,12.94c0.04-0.3,0.06-0.61,0.06-0.94c0-0.32-0.02-0.64-0.07-0.94l2.03-1.58c0.18-0.14,0.23-0.41,0.12-0.61 l-1.92-3.32c-0.12-0.22-0.37-0.29-0.59-0.22l-2.39,0.96c-0.5-0.38-1.03-0.7-1.62-0.94L14.4,2.81c-0.04-0.24-0.24-0.41-0.48-0.41 h-3.84c-0.24,0-0.43,0.17-0.47,0.41L9.25,5.35C8.66,5.59,8.12,5.92,7.63,6.29L5.24,5.33c-0.22-0.08-0.47,0-0.59,0.22L2.74,8.87 C2.62,9.08,2.66,9.34,2.86,9.48l2.03,1.58C4.84,11.36,4.82,11.69,4.82,12s0.02,0.64,0.07,0.94l-2.03,1.58 c-0.18,0.14-0.23,0.41-0.12,0.61l1.92,3.32c0.12,0.22,0.37,0.29,0.59,0.22l2.39-0.96c0.5,0.38,1.03,0.7,1.62,0.94l0.36,2.54 c0.05,0.24,0.24,0.41,0.48,0.41h3.84c0.24,0,0.44-0.17,0.47-0.41l0.36-2.54c0.59-0.24,1.13-0.56,1.62-0.94l2.39,0.96 c0.22,0.08,0.47,0,0.59-0.22l1.92-3.32c0.12-0.22,0.07-0.47-0.12-0.61L19.14,12.94z M12,15.6c-1.98,0-3.6-1.62-3.6-3.6 s1.62-3.6,3.6-3.6s3.6,1.62,3.6,3.6S13.98,15.6,12,15.6z"/>
							</svg>
						{:else if item.icon === 'upload'}
							<svg class="w-6 h-6 transition-colors duration-300" class:text-blue-400={isActive(item.path)} class:text-gray-400={!isActive(item.path)} fill="currentColor" viewBox="0 0 24 24">
								<path d="M14,2H6A2,2 0 0,0 4,4V20A2,2 0 0,0 6,22H18A2,2 0 0,0 20,20V8L14,2M18,20H6V4H13V9H18V20Z"/>
							</svg>
						{/if}
						{#if isActive(item.path)}
							<div class="absolute -bottom-2 left-1/2 transform -translate-x-1/2 w-1 h-1 bg-blue-400 rounded-full"></div>
						{/if}
					</div>
					<span class="text-xs font-medium transition-colors duration-300" class:text-blue-400={isActive(item.path)} class:text-gray-400={!isActive(item.path)}>{item.label}</span>
				</button>
			{/each}
		</div>
	</div>
</nav>

<!-- Mobile/Tablet Toolbar -->
<nav class="fixed bottom-0 left-0 right-0 z-50 md:hidden">
	<div class="glass border-t border-gray-600 px-6 py-4">
		<div class="flex justify-around items-center">
			{#each navigationItems as item}
				<button
					onclick={() => navigate(item.path)}
					class="group relative flex flex-col items-center space-y-1 p-3 rounded-2xl transition-all duration-300 ease-out hover:bg-gray-700 active:scale-95"
					class:active={isActive(item.path)}
					aria-label={item.ariaLabel}
				>
					<div class="relative">
						{#if item.icon === 'chat'}
							<svg class="w-7 h-7 transition-colors duration-300" class:text-blue-400={isActive(item.path)} class:text-gray-400={!isActive(item.path)} fill="currentColor" viewBox="0 0 24 24">
								<path d="M20 2H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h4l4 4 4-4h4c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm-2 12H6v-2h12v2zm0-3H6V9h12v2zm0-3H6V6h12v2z"/>
							</svg>
						{:else if item.icon === 'settings'}
							<svg class="w-7 h-7 transition-colors duration-300" class:text-blue-400={isActive(item.path)} class:text-gray-400={!isActive(item.path)} fill="currentColor" viewBox="0 0 24 24">
								<path d="M19.14,12.94c0.04-0.3,0.06-0.61,0.06-0.94c0-0.32-0.02-0.64-0.07-0.94l2.03-1.58c0.18-0.14,0.23-0.41,0.12-0.61 l-1.92-3.32c-0.12-0.22-0.37-0.29-0.59-0.22l-2.39,0.96c-0.5-0.38-1.03-0.7-1.62-0.94L14.4,2.81c-0.04-0.24-0.24-0.41-0.48-0.41 h-3.84c-0.24,0-0.43,0.17-0.47,0.41L9.25,5.35C8.66,5.59,8.12,5.92,7.63,6.29L5.24,5.33c-0.22-0.08-0.47,0-0.59,0.22L2.74,8.87 C2.62,9.08,2.66,9.34,2.86,9.48l2.03,1.58C4.84,11.36,4.82,11.69,4.82,12s0.02,0.64,0.07,0.94l-2.03,1.58 c-0.18,0.14-0.23,0.41-0.12,0.61l1.92,3.32c0.12,0.22,0.37,0.29,0.59,0.22l2.39-0.96c0.5,0.38,1.03,0.7,1.62,0.94l0.36,2.54 c0.05,0.24,0.24,0.41,0.48,0.41h3.84c0.24,0,0.44-0.17,0.47-0.41l0.36-2.54c0.59-0.24,1.13-0.56,1.62-0.94l2.39,0.96 c0.22,0.08,0.47,0,0.59-0.22l1.92-3.32c0.12-0.22,0.07-0.47-0.12-0.61L19.14,12.94z M12,15.6c-1.98,0-3.6-1.62-3.6-3.6 s1.62-3.6,3.6-3.6s3.6,1.62,3.6,3.6S13.98,15.6,12,15.6z"/>
							</svg>
						{:else if item.icon === 'upload'}
							<svg class="w-7 h-7 transition-colors duration-300" class:text-blue-400={isActive(item.path)} class:text-gray-400={!isActive(item.path)} fill="currentColor" viewBox="0 0 24 24">
								<path d="M14,2H6A2,2 0 0,0 4,4V20A2,2 0 0,0 6,22H18A2,2 0 0,0 20,20V8L14,2M18,20H6V4H13V9H18V20Z"/>
							</svg>
						{/if}
						{#if isActive(item.path)}
							<div class="absolute -top-1 -right-1 w-2 h-2 bg-blue-400 rounded-full"></div>
						{/if}
					</div>
				</button>
			{/each}
		</div>
	</div>
</nav>

<style>
	.active {
		background-color: rgba(255, 255, 255, 0.1);
	}
</style>