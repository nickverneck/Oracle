<script lang="ts">
	import { page } from '$app/stores';
	
	export let title: string = 'Oracle';
	export let subtitle: string = '';
	
	$: currentPage = $page.url.pathname;
</script>

<header class="fixed top-0 left-0 right-0 z-40 bg-white/5 backdrop-blur-md border-b border-white/10">
	<div class="max-w-4xl mx-auto px-4 py-4">
		<div class="flex items-center justify-between">
			<div>
				<h1 class="text-xl font-bold text-white">{title}</h1>
				{#if subtitle}
					<p class="text-sm text-gray-300 mt-1">{subtitle}</p>
				{/if}
			</div>
			
			<div class="flex items-center space-x-2">
				{#if currentPage === '/'}
					<span class="px-3 py-1 bg-blue-500/20 text-blue-300 rounded-full text-xs font-medium">Chat</span>
				{:else if currentPage === '/settings'}
					<span class="px-3 py-1 bg-purple-500/20 text-purple-300 rounded-full text-xs font-medium">Settings</span>
				{:else if currentPage === '/data'}
					<span class="px-3 py-1 bg-green-500/20 text-green-300 rounded-full text-xs font-medium">Data Ingestion</span>
				{/if}
			</div>
		</div>
	</div>
</header>
