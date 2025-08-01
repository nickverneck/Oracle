import { test, expect } from '@playwright/test';

test.describe('Oracle Settings Page', () => {
	test.beforeEach(async ({ page }) => {
		await page.goto('/settings');
	});

	test('should display the settings interface', async ({ page }) => {
		// Check page title
		await expect(page).toHaveTitle('Settings - Oracle');
		
		// Check header elements
		await expect(page.locator('h1')).toContainText('Settings');
		await expect(page.locator('text=Configure Oracle')).toBeVisible();
		
		// Check tab navigation
		await expect(page.locator('text=Providers')).toBeVisible();
		await expect(page.locator('text=General')).toBeVisible();
	});

	test('should show provider configurations', async ({ page }) => {
		// Check that all providers are listed
		await expect(page.locator('text=LLVM (Default)')).toBeVisible();
		await expect(page.locator('text=Ollama')).toBeVisible();
		await expect(page.locator('text=Google Gemini')).toBeVisible();
		
		// Check that LLVM is enabled by default
		const llvmToggle = page.locator('text=LLVM (Default)').locator('..').locator('button').first();
		await expect(llvmToggle).toHaveClass(/bg-blue-500/);
	});

	test('should toggle provider settings', async ({ page }) => {
		// Find and click the Ollama toggle
		const ollamaSection = page.locator('text=Ollama').locator('..');
		const ollamaToggle = ollamaSection.locator('button').first();
		
		// Toggle Ollama on
		await ollamaToggle.click();
		
		// Check that Ollama configuration fields appear
		await expect(page.locator('text=Ollama URL')).toBeVisible();
		await expect(page.locator('input[placeholder="http://localhost:11434"]')).toBeVisible();
	});

	test('should show API key field for Gemini', async ({ page }) => {
		// Find and click the Gemini toggle
		const geminiSection = page.locator('text=Google Gemini').locator('..');
		const geminiToggle = geminiSection.locator('button').first();
		
		// Toggle Gemini on
		await geminiToggle.click();
		
		// Check that API key field appears
		await expect(page.locator('text=API Key')).toBeVisible();
		await expect(page.locator('input[placeholder="Enter your Gemini API key"]')).toBeVisible();
	});

	test('should toggle API key visibility', async ({ page }) => {
		// Enable Gemini first
		const geminiToggle = page.locator('text=Google Gemini').locator('..').locator('button').first();
		await geminiToggle.click();
		
		// Find the API key input and visibility toggle
		const apiKeyInput = page.locator('input[placeholder="Enter your Gemini API key"]');
		const visibilityToggle = apiKeyInput.locator('..').locator('button').last();
		
		// Initially should be password type
		await expect(apiKeyInput).toHaveAttribute('type', 'password');
		
		// Click visibility toggle
		await visibilityToggle.click();
		
		// Should now be text type
		await expect(apiKeyInput).toHaveAttribute('type', 'text');
	});

	test('should update provider configurations', async ({ page }) => {
		// Enable Ollama
		const ollamaToggle = page.locator('text=Ollama').locator('..').locator('button').first();
		await ollamaToggle.click();
		
		// Update URL
		const urlInput = page.locator('input[placeholder="http://localhost:11434"]');
		await urlInput.fill('http://localhost:8080');
		
		// Update model
		const modelInput = page.locator('text=Ollama').locator('..').locator('input[placeholder="Enter model name"]');
		await modelInput.fill('custom-model');
		
		// Save settings
		await page.locator('text=Save Settings').click();
		
		// Check that values are preserved
		await expect(urlInput).toHaveValue('http://localhost:8080');
		await expect(modelInput).toHaveValue('custom-model');
	});

	test('should switch between tabs', async ({ page }) => {
		// Click General tab
		await page.locator('text=General').click();
		
		// Check that general settings content is shown
		await expect(page.locator('text=General Settings')).toBeVisible();
		await expect(page.locator('text=General settings will be available in future updates.')).toBeVisible();
		
		// Switch back to Providers
		await page.locator('text=Providers').click();
		
		// Check that provider settings are shown again
		await expect(page.locator('text=LLVM (Default)')).toBeVisible();
	});

	test('should have working action buttons', async ({ page }) => {
		// Check that action buttons are present
		await expect(page.locator('text=Save Settings')).toBeVisible();
		await expect(page.locator('text=Reset to Defaults')).toBeVisible();
		
		// Buttons should be clickable
		await expect(page.locator('text=Save Settings')).toBeEnabled();
		await expect(page.locator('text=Reset to Defaults')).toBeEnabled();
	});

	test('should be responsive on mobile', async ({ page }) => {
		// Set mobile viewport
		await page.setViewportSize({ width: 375, height: 667 });
		
		// Check that mobile toolbar is visible
		await expect(page.locator('nav.md\\:hidden')).toBeVisible();
		
		// Check that settings interface is still usable
		await expect(page.locator('text=Providers')).toBeVisible();
		await expect(page.locator('text=LLVM (Default)')).toBeVisible();
	});
});
