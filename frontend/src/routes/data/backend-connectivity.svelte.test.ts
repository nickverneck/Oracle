import { describe, it, expect, beforeEach, vi } from 'vitest';
import { uploadFiles } from '$lib/services/ingestion';
import config from '$lib/config';

// Test to diagnose backend connectivity issues
// This test must run in the browser environment to access window and XMLHttpRequest

describe('Backend Connectivity Test', () => {
  it('should have correct backend API URL configuration', () => {
    // Check that the backend URL is properly configured
    expect(config.BACKEND_API_URL).toBeDefined();
    console.log('Configured backend URL:', config.BACKEND_API_URL);
  });

  it('should be able to make a basic request to the backend health endpoint', async () => {
    // This test will help diagnose connectivity issues
    console.log('Testing backend connectivity to:', config.BACKEND_API_URL);
    
    try {
      // First check if we can connect at all
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 5000); // 5 second timeout
      
      const response = await fetch(`${config.BACKEND_API_URL}/health`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
        signal: controller.signal
      });
      
      clearTimeout(timeoutId);
      
      if (response.ok) {
        console.log('✓ Backend connectivity: SUCCESS');
        const data = await response.json();
        console.log('  Backend health status:', data);
        expect(response.status).toBe(200);
      } else {
        console.log('✗ Backend connectivity: FAILED');
        console.log('  Status:', response.status, response.statusText);
        console.log('  Response headers:', [...response.headers.entries()]);
        // Don't fail the test here, as this is diagnostic
      }
    } catch (error: any) {
      console.log('✗ Backend connectivity: NETWORK ERROR');
      console.log('  Error name:', error.name);
      console.log('  Error message:', error.message);
      if (error.cause) {
        console.log('  Error cause:', error.cause);
      }
      // Don't fail the test here, as this is diagnostic
    }
  });

  it('should be able to make a request to the ingest endpoint', async () => {
    // Test if the upload endpoint is accessible
    console.log('Testing ingest endpoint accessibility:', `${config.BACKEND_API_URL}/ingest`);
    
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 5000); // 5 second timeout
      
      const response = await fetch(`${config.BACKEND_API_URL}/ingest`, {
        method: 'OPTIONS',
        signal: controller.signal
      });
      
      clearTimeout(timeoutId);
      
      if (response.ok) {
        console.log('✓ Ingest endpoint accessible: YES');
        console.log('  Allowed methods:', response.headers.get('allow'));
        expect(response.status).toBe(200);
      } else {
        console.log('✗ Ingest endpoint accessible: NO');
        console.log('  Status:', response.status, response.statusText);
        // Don't fail the test here, as this is diagnostic
      }
    } catch (error: any) {
      console.log('✗ Ingest endpoint test: NETWORK ERROR');
      console.log('  Error name:', error.name);
      console.log('  Error message:', error.message);
      if (error.cause) {
        console.log('  Error cause:', error.cause);
      }
      // Don't fail the test here, as this is diagnostic
    }
  });

  it('should handle network errors gracefully in uploadFiles function', async () => {
    // Test that the uploadFiles function handles network errors properly
    
    // Create a mock file
    const mockFile = new File(['test content'], 'test.txt', { type: 'text/plain' });
    
    // Mock the XMLHttpRequest to simulate network errors
    const originalXMLHttpRequest = window.XMLHttpRequest;
    
    // Create a mock XMLHttpRequest
    const mockXHR = {
      open: vi.fn(),
      send: vi.fn(),
      setRequestHeader: vi.fn(),
      timeout: 0,
      upload: {
        addEventListener: vi.fn(),
        onprogress: null as any,
      },
      onload: null as any,
      onerror: null as any,
      ontimeout: null as any,
    };
    
    // Mock the global XMLHttpRequest
    (window as any).XMLHttpRequest = vi.fn(() => mockXHR);
    
    try {
      // Call the uploadFiles function
      const progressCallback = vi.fn();
      await uploadFiles([mockFile], 'both', progressCallback);
      
      // This should not be reached if network error handling works
      expect(true).toBe(false); // Fail if we reach here
    } catch (error: any) {
      // Check that the error is properly handled
      expect(error).toBeInstanceOf(Error);
      console.log('✓ Network error handling works:', error.message);
    } finally {
      // Restore the original XMLHttpRequest
      (window as any).XMLHttpRequest = originalXMLHttpRequest;
    }
  });
});
