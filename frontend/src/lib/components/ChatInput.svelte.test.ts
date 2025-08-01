import { render, screen, fireEvent } from '@testing-library/svelte';
import { vi } from 'vitest';
import ChatInput from './ChatInput.svelte';

// Mock Speech Recognition API
const mockSpeechRecognition = {
	start: vi.fn(),
	stop: vi.fn(),
	onstart: null,
	onresult: null,
	onend: null,
	onerror: null,
	continuous: false,
	interimResults: false,
	lang: 'en-US'
};

Object.defineProperty(window, 'SpeechRecognition', {
	writable: true,
	value: vi.fn(() => mockSpeechRecognition)
});

Object.defineProperty(window, 'webkitSpeechRecognition', {
	writable: true,
	value: vi.fn(() => mockSpeechRecognition)
});

describe('ChatInput Component', () => {
	test('renders input field and buttons', () => {
		render(ChatInput);
		
		expect(screen.getByPlaceholderText('Ask Oracle anything...')).toBeInTheDocument();
		expect(screen.getByLabelText('Start voice input')).toBeInTheDocument();
		expect(screen.getByLabelText('Send message')).toBeInTheDocument();
	});

	test('enables send button when message is entered', async () => {
		render(ChatInput);
		
		const input = screen.getByPlaceholderText('Ask Oracle anything...');
		const sendButton = screen.getByLabelText('Send message');
		
		expect(sendButton).toBeDisabled();
		
		await fireEvent.input(input, { target: { value: 'Hello Oracle' } });
		
		expect(sendButton).not.toBeDisabled();
	});

	test('dispatches send event when form is submitted', async () => {
		const component = render(ChatInput);
		let dispatchedEvent: any = null;
		
		component.component.$on('send', (event) => {
			dispatchedEvent = event.detail;
		});
		
		const input = screen.getByPlaceholderText('Ask Oracle anything...');
		const sendButton = screen.getByLabelText('Send message');
		
		await fireEvent.input(input, { target: { value: 'Test message' } });
		await fireEvent.click(sendButton);
		
		expect(dispatchedEvent).toEqual({ message: 'Test message' });
	});

	test('sends message on Enter key press', async () => {
		const component = render(ChatInput);
		let dispatchedEvent: any = null;
		
		component.component.$on('send', (event) => {
			dispatchedEvent = event.detail;
		});
		
		const input = screen.getByPlaceholderText('Ask Oracle anything...');
		
		await fireEvent.input(input, { target: { value: 'Test message' } });
		await fireEvent.keyDown(input, { key: 'Enter' });
		
		expect(dispatchedEvent).toEqual({ message: 'Test message' });
	});

	test('does not send message on Shift+Enter', async () => {
		const component = render(ChatInput);
		let dispatchedEvent: any = null;
		
		component.component.$on('send', (event) => {
			dispatchedEvent = event.detail;
		});
		
		const input = screen.getByPlaceholderText('Ask Oracle anything...');
		
		await fireEvent.input(input, { target: { value: 'Test message' } });
		await fireEvent.keyDown(input, { key: 'Enter', shiftKey: true });
		
		expect(dispatchedEvent).toBeNull();
	});

	test('dictation button changes state when recording', async () => {
		render(ChatInput);
		
		const dictationButton = screen.getByLabelText('Start voice input');
		
		await fireEvent.click(dictationButton);
		
		expect(mockSpeechRecognition.start).toHaveBeenCalled();
	});

	test('shows listening indicator when recording', async () => {
		render(ChatInput);
		
		const dictationButton = screen.getByLabelText('Start voice input');
		
		// Simulate starting recording
		await fireEvent.click(dictationButton);
		
		// Simulate speech recognition starting
		if (mockSpeechRecognition.onstart) {
			mockSpeechRecognition.onstart();
		}
		
		expect(screen.getByText('Listening...')).toBeInTheDocument();
	});
});
