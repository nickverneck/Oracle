import { test, expect } from '@playwright/test';

test.describe('Oracle Chat Interface', () => {
	test.beforeEach(async ({ page }) => {
		await page.goto('/');
	});

	test('should display the main chat interface', async ({ page }) => {
		// Check page title
		await expect(page).toHaveTitle('Oracle - AI Knowledge Assistant');
		
		// Check header elements
		await expect(page.locator('h1')).toContainText('Oracle');
		await expect(page.locator('text=AI Knowledge Assistant')).toBeVisible();
		await expect(page.locator('text=Online')).toBeVisible();
		
		// Check chat input is present
		await expect(page.locator('textarea[placeholder="Ask Oracle anything..."]')).toBeVisible();
		
		// Check toolbar is present
		await expect(page.locator('nav').first()).toBeVisible();
	});

	test('should show welcome message on load', async ({ page }) => {
		// Check that the welcome message is displayed
		await expect(page.locator('text=Hello! I\'m Oracle')).toBeVisible();
	});

	test('should enable send button when text is entered', async ({ page }) => {
		const input = page.locator('textarea[placeholder="Ask Oracle anything..."]');
		const sendButton = page.locator('button[aria-label="Send message"]');
		
		// Send button should be disabled initially
		await expect(sendButton).toBeDisabled();
		
		// Type a message
		await input.fill('Hello Oracle');
		
		// Send button should now be enabled
		await expect(sendButton).toBeEnabled();
	});

	test('should send message and show response', async ({ page }) => {
		const input = page.locator('textarea[placeholder="Ask Oracle anything..."]');
		const sendButton = page.locator('button[aria-label="Send message"]');
		
		// Type and send a message
		await input.fill('What is artificial intelligence?');
		await sendButton.click();
		
		// Check that user message appears
		await expect(page.locator('text=What is artificial intelligence?')).toBeVisible();
		
		// Check that loading indicator appears
		await expect(page.locator('text=Oracle is thinking...')).toBeVisible();
		
		// Wait for response (with timeout)
		await expect(page.locator('text=I understand you\'re asking about')).toBeVisible({ timeout: 10000 });
		
		// Input should be cleared
		await expect(input).toHaveValue('');
	});

	test('should send message with Enter key', async ({ page }) => {
		const input = page.locator('textarea[placeholder="Ask Oracle anything..."]');
		
		// Type a message
		await input.fill('Test message');
		
		// Press Enter
		await input.press('Enter');
		
		// Check that message was sent
		await expect(page.locator('text=Test message')).toBeVisible();
	});

	test('should not send message with Shift+Enter', async ({ page }) => {
		const input = page.locator('textarea[placeholder="Ask Oracle anything..."]');
		
		// Type a message
		await input.fill('Test message');
		
		// Press Shift+Enter
		await input.press('Shift+Enter');
		
		// Message should still be in input
		await expect(input).toHaveValue('Test message');
	});

	test('should show dictation button', async ({ page }) => {
		const dictationButton = page.locator('button[aria-label="Start voice input"]');
		await expect(dictationButton).toBeVisible();
	});

	test('should be responsive on mobile', async ({ page }) => {
		// Set mobile viewport
		await page.setViewportSize({ width: 375, height: 667 });
		
		// Check that mobile toolbar is visible
		await expect(page.locator('nav.md\\:hidden')).toBeVisible();
		
		// Check that desktop toolbar is hidden
		await expect(page.locator('nav.hidden.md\\:block')).toBeHidden();
		
		// Check that chat interface still works
		await expect(page.locator('textarea[placeholder="Ask Oracle anything..."]')).toBeVisible();
	});
});
