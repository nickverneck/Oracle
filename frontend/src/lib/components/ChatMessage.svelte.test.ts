import { render, screen } from '@testing-library/svelte';
import ChatMessage from './ChatMessage.svelte';

describe('ChatMessage Component', () => {
	const mockUserMessage = {
		id: '1',
		content: 'Hello, how are you?',
		role: 'user' as const,
		timestamp: new Date('2024-01-01T12:00:00Z')
	};

	const mockAssistantMessage = {
		id: '2',
		content: 'I am doing well, thank you for asking!',
		role: 'assistant' as const,
		timestamp: new Date('2024-01-01T12:01:00Z')
	};

	test('renders user message correctly', () => {
		render(ChatMessage, { props: { message: mockUserMessage } });
		
		expect(screen.getByText('Hello, how are you?')).toBeInTheDocument();
		expect(screen.getByText('12:00 PM')).toBeInTheDocument();
	});

	test('renders assistant message correctly', () => {
		render(ChatMessage, { props: { message: mockAssistantMessage } });
		
		expect(screen.getByText('I am doing well, thank you for asking!')).toBeInTheDocument();
		expect(screen.getByText('12:01 PM')).toBeInTheDocument();
	});

	test('applies correct styling for user messages', () => {
		render(ChatMessage, { props: { message: mockUserMessage } });
		
		const messageContainer = screen.getByText('Hello, how are you?').closest('div');
		expect(messageContainer).toHaveClass('bg-blue-500');
	});

	test('applies correct styling for assistant messages', () => {
		render(ChatMessage, { props: { message: mockAssistantMessage } });
		
		const messageContainer = screen.getByText('I am doing well, thank you for asking!').closest('div');
		expect(messageContainer).toHaveClass('bg-white');
	});

	test('shows user avatar for user messages', () => {
		render(ChatMessage, { props: { message: mockUserMessage } });
		
		const userIcon = document.querySelector('svg');
		expect(userIcon).toBeInTheDocument();
	});

	test('shows assistant avatar for assistant messages', () => {
		render(ChatMessage, { props: { message: mockAssistantMessage } });
		
		const assistantIcon = document.querySelector('svg');
		expect(assistantIcon).toBeInTheDocument();
	});

	test('formats timestamp correctly', () => {
		const message = {
			...mockUserMessage,
			timestamp: new Date('2024-01-01T09:30:00Z')
		};
		
		render(ChatMessage, { props: { message } });
		
		expect(screen.getByText('9:30 AM')).toBeInTheDocument();
	});

	test('handles multiline content', () => {
		const multilineMessage = {
			...mockUserMessage,
			content: 'Line 1\nLine 2\nLine 3'
		};
		
		render(ChatMessage, { props: { message: multilineMessage } });
		
		const messageElement = screen.getByText(/Line 1/);
		expect(messageElement).toHaveClass('whitespace-pre-wrap');
	});
});
