<script lang="ts">
	export let message: {
		id: string;
		content: string;
		role: 'user' | 'assistant';
		timestamp: Date;
	};

	function formatTime(date: Date): string {
		return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
	}
</script>

<div class="flex {message.role === 'user' ? 'justify-end' : 'justify-start'} mb-4">
	<div class="max-w-[80%] {message.role === 'user' ? 'order-2' : 'order-1'}">
		<!-- Message Bubble -->
		<div 
			class="px-4 py-3 rounded-2xl shadow-lg transition-all duration-300 ease-out hover:shadow-xl {message.role === 'user' ? 'bg-blue-500' : 'glass'}"
		>
			<div class="text-white whitespace-pre-wrap break-words">
				{message.content}
			</div>
		</div>
		
		<!-- Timestamp -->
		<div class="text-xs text-gray-400 mt-1 {message.role === 'user' ? 'text-right' : 'text-left'}">
			{formatTime(message.timestamp)}
		</div>
	</div>
	
	<!-- Avatar -->
	<div class="w-8 h-8 rounded-full flex items-center justify-center {message.role === 'user' ? 'order-1 mr-3 bg-blue-500' : 'order-2 ml-3 glass'}">
		{#if message.role === 'user'}
			<svg class="w-4 h-4 text-white" fill="currentColor" viewBox="0 0 24 24">
				<path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/>
			</svg>
		{:else}
			<svg class="w-4 h-4 text-blue-400" fill="currentColor" viewBox="0 0 24 24">
				<path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
			</svg>
		{/if}
	</div>
</div>
