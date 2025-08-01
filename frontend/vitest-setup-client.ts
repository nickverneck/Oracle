/// <reference types="@vitest/browser/matchers" />
/// <reference types="@vitest/browser/providers/playwright" />

import '@testing-library/jest-dom';

// Setup for Svelte component testing
import { beforeEach } from 'vitest';

beforeEach(() => {
	// Clean up DOM after each test
	document.body.innerHTML = '';
});
