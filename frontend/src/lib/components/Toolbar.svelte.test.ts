import { render, screen } from '@testing-library/svelte';
import { vi } from 'vitest';
import Toolbar from './Toolbar.svelte';

// Mock SvelteKit modules
vi.mock('$app/stores', () => ({
	page: {
		subscribe: vi.fn((callback) => {
			callback({ url: { pathname: '/' } });
			return () => {};
		})
	}
}));

vi.mock('$app/navigation', () => ({
	goto: vi.fn()
}));

describe('Toolbar Component', () => {
	test('renders navigation items correctly', () => {
		render(Toolbar);
		
		expect(screen.getByLabelText('Go to chat')).toBeInTheDocument();
		expect(screen.getByLabelText('Go to settings')).toBeInTheDocument();
		expect(screen.getByLabelText('Go to data ingestion')).toBeInTheDocument();
	});

	test('shows desktop toolbar on larger screens', () => {
		render(Toolbar);
		
		const desktopNav = document.querySelector('.hidden.md\\:block');
		expect(desktopNav).toBeInTheDocument();
	});

	test('shows mobile toolbar on smaller screens', () => {
		render(Toolbar);
		
		const mobileNav = document.querySelector('.md\\:hidden');
		expect(mobileNav).toBeInTheDocument();
	});

	test('applies active state to current page', () => {
		render(Toolbar);
		
		const chatButtons = screen.getAllByLabelText('Go to chat');
		chatButtons.forEach(button => {
			expect(button).toHaveClass('active');
		});
	});

	test('has proper accessibility attributes', () => {
		render(Toolbar);
		
		const buttons = screen.getAllByRole('button');
		buttons.forEach(button => {
			expect(button).toHaveAttribute('aria-label');
		});
	});
});
