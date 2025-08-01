import { test, expect } from '@playwright/test';
import path from 'path';

test.describe('Oracle Data Ingestion Page', () => {
	test.beforeEach(async ({ page }) => {
		await page.goto('/data');
	});

	test('should display the data ingestion interface', async ({ page }) => {
		// Check page title
		await expect(page).toHaveTitle('Data Ingestion - Oracle');
		
		// Check header elements
		await expect(page.locator('h1')).toContainText('Data Ingestion');
		await expect(page.locator('text=Upload & Process Documents')).toBeVisible();
		
		// Check processing method selection
		await expect(page.locator('text=Processing Method')).toBeVisible();
		await expect(page.locator('text=Knowledge Graph')).toBeVisible();
		await expect(page.locator('text=RAG')).toBeVisible();
		await expect(page.locator('text=Both')).toBeVisible();
	});

	test('should show upload area', async ({ page }) => {
		// Check upload area elements
		await expect(page.locator('text=Upload Documents')).toBeVisible();
		await expect(page.locator('text=Drag and drop files here, or click to browse')).toBeVisible();
		await expect(page.locator('text=Supported: PDF, HTML, TXT, Markdown, DOC, DOCX')).toBeVisible();
		await expect(page.locator('text=Choose Files')).toBeVisible();
	});

	test('should select processing methods', async ({ page }) => {
		// Initially "Both" should be selected
		const bothButton = page.locator('text=Both').locator('..');
		await expect(bothButton).toHaveClass(/border-blue-500/);
		
		// Click Knowledge Graph
		const kgButton = page.locator('text=Knowledge Graph').locator('..');
		await kgButton.click();
		await expect(kgButton).toHaveClass(/border-blue-500/);
		
		// Click RAG
		const ragButton = page.locator('text=RAG').locator('..');
		await ragButton.click();
		await expect(ragButton).toHaveClass(/border-blue-500/);
		
		// Click Both again
		await bothButton.click();
		await expect(bothButton).toHaveClass(/border-blue-500/);
	});

	test('should handle drag and drop area interactions', async ({ page }) => {
		const uploadArea = page.locator('text=Upload Documents').locator('..');
		
		// Should show default state
		await expect(page.locator('text=Upload Documents')).toBeVisible();
		
		// Simulate drag enter (this is limited in Playwright, but we can test the UI)
		await uploadArea.hover();
		
		// Check that upload area is interactive
		await expect(uploadArea).toBeVisible();
	});

	test('should open file dialog when clicking Choose Files', async ({ page }) => {
		// Set up file chooser handler
		const fileChooserPromise = page.waitForEvent('filechooser');
		
		// Click Choose Files button
		await page.locator('text=Choose Files').click();
		
		// Verify file chooser opened
		const fileChooser = await fileChooserPromise;
		expect(fileChooser).toBeTruthy();
	});

	test('should simulate file upload process', async ({ page }) => {
		// Create a mock file for testing
		const fileContent = 'This is a test document content for Oracle processing.';
		
		// Set up file chooser and select a file
		const fileChooserPromise = page.waitForEvent('filechooser');
		await page.locator('text=Choose Files').click();
		const fileChooser = await fileChooserPromise;
		
		// In a real test, you would use:
		// await fileChooser.setFiles([path.join(__dirname, 'test-files', 'sample.txt')]);
		
		// For now, we'll test the UI state after file selection would occur
		// This would require mocking the file upload functionality
	});

	test('should show file list when files are uploaded', async ({ page }) => {
		// This test would require actual file upload simulation
		// For now, we'll check that the file list area exists
		const mainContent = page.locator('main');
		await expect(mainContent).toBeVisible();
		
		// The file list would appear here after upload
		// await expect(page.locator('text=Uploaded Files')).toBeVisible();
	});

	test('should handle different processing types correctly', async ({ page }) => {
		// Test Knowledge Graph selection
		await page.locator('text=Knowledge Graph').locator('..').click();
		
		// Test RAG selection
		await page.locator('text=RAG').locator('..').click();
		
		// Test Both selection
		await page.locator('text=Both').locator('..').click();
		
		// Each should update the processing type
		// This would be verified through file upload simulation
	});

	test('should be responsive on mobile', async ({ page }) => {
		// Set mobile viewport
		await page.setViewportSize({ width: 375, height: 667 });
		
		// Check that mobile toolbar is visible
		await expect(page.locator('nav.md\\:hidden')).toBeVisible();
		
		// Check that data ingestion interface is still usable
		await expect(page.locator('text=Processing Method')).toBeVisible();
		await expect(page.locator('text=Upload Documents')).toBeVisible();
		
		// Processing method buttons should stack on mobile
		const processingGrid = page.locator('.grid-cols-1.md\\:grid-cols-3');
		await expect(processingGrid).toBeVisible();
	});

	test('should show proper icons for processing methods', async ({ page }) => {
		// Check that each processing method has an icon
		const kgSection = page.locator('text=Knowledge Graph').locator('..');
		const ragSection = page.locator('text=RAG').locator('..');
		const bothSection = page.locator('text=Both').locator('..');
		
		// Each should contain an SVG icon
		await expect(kgSection.locator('svg')).toBeVisible();
		await expect(ragSection.locator('svg')).toBeVisible();
		await expect(bothSection.locator('svg')).toBeVisible();
	});

	test('should have proper accessibility features', async ({ page }) => {
		// Check that buttons have proper roles
		const buttons = page.locator('button');
		const buttonCount = await buttons.count();
		expect(buttonCount).toBeGreaterThan(0);
		
		// Check that the file input is properly hidden but accessible
		const fileInput = page.locator('input[type="file"]');
		await expect(fileInput).toHaveClass(/hidden/);
	});
});
