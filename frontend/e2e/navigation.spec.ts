import { test, expect } from '@playwright/test';

test.describe('Oracle Navigation', () => {
	test('should navigate between all pages using toolbar', async ({ page }) => {
		// Start at home page
		await page.goto('/');
		await expect(page).toHaveTitle('Oracle - AI Knowledge Assistant');
		
		// Navigate to Settings
		await page.locator('button[aria-label="Go to settings"]').first().click();
		await expect(page).toHaveTitle('Settings - Oracle');
		await expect(page.locator('h1')).toContainText('Settings');
		
		// Navigate to Data Ingestion
		await page.locator('button[aria-label="Go to data ingestion"]').first().click();
		await expect(page).toHaveTitle('Data Ingestion - Oracle');
		await expect(page.locator('h1')).toContainText('Data Ingestion');
		
		// Navigate back to Chat
		await page.locator('button[aria-label="Go to chat"]').first().click();
		await expect(page).toHaveTitle('Oracle - AI Knowledge Assistant');
		await expect(page.locator('h1')).toContainText('Oracle');
	});

	test('should show active state in toolbar', async ({ page }) => {
		// Start at home page
		await page.goto('/');
		
		// Chat button should be active
		const chatButton = page.locator('button[aria-label="Go to chat"]').first();
		await expect(chatButton).toHaveClass(/active/);
		
		// Navigate to settings
		await page.locator('button[aria-label="Go to settings"]').first().click();
		
		// Settings button should now be active
		const settingsButton = page.locator('button[aria-label="Go to settings"]').first();
		await expect(settingsButton).toHaveClass(/active/);
		
		// Chat button should no longer be active
		await expect(chatButton).not.toHaveClass(/active/);
	});

	test('should work on both desktop and mobile toolbars', async ({ page }) => {
		await page.goto('/');
		
		// Test desktop navigation
		await page.setViewportSize({ width: 1024, height: 768 });
		
		// Desktop toolbar should be visible
		await expect(page.locator('nav.hidden.md\\:block')).toBeVisible();
		
		// Navigate using desktop toolbar
		await page.locator('nav.hidden.md\\:block button[aria-label="Go to settings"]').click();
		await expect(page).toHaveTitle('Settings - Oracle');
		
		// Test mobile navigation
		await page.setViewportSize({ width: 375, height: 667 });
		
		// Mobile toolbar should be visible
		await expect(page.locator('nav.md\\:hidden')).toBeVisible();
		
		// Navigate using mobile toolbar
		await page.locator('nav.md\\:hidden button[aria-label="Go to data ingestion"]').click();
		await expect(page).toHaveTitle('Data Ingestion - Oracle');
	});

	test('should maintain consistent layout across pages', async ({ page }) => {
		const pages = [
			{ url: '/', title: 'Oracle - AI Knowledge Assistant' },
			{ url: '/settings', title: 'Settings - Oracle' },
			{ url: '/data', title: 'Data Ingestion - Oracle' }
		];

		for (const pageInfo of pages) {
			await page.goto(pageInfo.url);
			await expect(page).toHaveTitle(pageInfo.title);
			
			// Check that header is present
			await expect(page.locator('header')).toBeVisible();
			
			// Check that main content is present
			await expect(page.locator('main')).toBeVisible();
			
			// Check that toolbar is present
			await expect(page.locator('nav').first()).toBeVisible();
			
			// Check consistent background
			const mainContainer = page.locator('.min-h-screen').first();
			await expect(mainContainer).toHaveClass(/bg-gradient-to-br/);
		}
	});

	test('should have proper glassmorphism effects', async ({ page }) => {
		await page.goto('/');
		
		// Check header glassmorphism
		const header = page.locator('header');
		await expect(header).toHaveClass(/backdrop-blur-md/);
		await expect(header).toHaveClass(/bg-white\/5/);
		
		// Check toolbar glassmorphism (desktop)
		await page.setViewportSize({ width: 1024, height: 768 });
		const desktopToolbar = page.locator('nav.hidden.md\\:block > div');
		await expect(desktopToolbar).toHaveClass(/backdrop-blur-md/);
		await expect(desktopToolbar).toHaveClass(/bg-white\/10/);
		
		// Check toolbar glassmorphism (mobile)
		await page.setViewportSize({ width: 375, height: 667 });
		const mobileToolbar = page.locator('nav.md\\:hidden > div');
		await expect(mobileToolbar).toHaveClass(/backdrop-blur-md/);
		await expect(mobileToolbar).toHaveClass(/bg-white\/10/);
	});

	test('should have smooth animations on interactions', async ({ page }) => {
		await page.goto('/');
		
		// Check that buttons have transition classes
		const buttons = page.locator('button');
		const buttonCount = await buttons.count();
		
		for (let i = 0; i < Math.min(buttonCount, 5); i++) {
			const button = buttons.nth(i);
			await expect(button).toHaveClass(/transition/);
		}
		
		// Test hover effects (limited in Playwright, but we can check classes)
		const toolbarButton = page.locator('button[aria-label="Go to settings"]').first();
		await expect(toolbarButton).toHaveClass(/hover:scale-105/);
	});

	test('should be accessible with keyboard navigation', async ({ page }) => {
		await page.goto('/');
		
		// Tab through navigation elements
		await page.keyboard.press('Tab');
		
		// Check that focus is visible
		const focusedElement = page.locator(':focus');
		await expect(focusedElement).toBeVisible();
		
		// Continue tabbing to reach toolbar
		for (let i = 0; i < 10; i++) {
			await page.keyboard.press('Tab');
			const currentFocus = page.locator(':focus');
			if (await currentFocus.getAttribute('aria-label') === 'Go to settings') {
				// Press Enter to navigate
				await page.keyboard.press('Enter');
				await expect(page).toHaveTitle('Settings - Oracle');
				break;
			}
		}
	});
});
