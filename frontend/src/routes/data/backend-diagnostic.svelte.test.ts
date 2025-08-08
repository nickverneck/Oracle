import { describe, it, expect } from 'vitest';
import config from '$lib/config';

// Simple diagnostic test to check backend connectivity
// This test runs in the browser environment

describe('Backend Diagnostic Test', () => {
  it('should have correct backend API URL configuration', () => {
    // Check that the backend URL is properly configured
    expect(config.BACKEND_API_URL).toBeDefined();
    console.log('Configured backend URL:', config.BACKEND_API_URL);
  });

  it('should be able to make a request to the backend', async () => {
    // This test will help diagnose connectivity issues
    console.log('Testing backend connectivity to:', config.BACKEND_API_URL);
    
    // Try to make a request to the health endpoint
    try {
      const response = await fetch(`${config.BACKEND_API_URL}/health`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      
      console.log('Response status:', response.status);
      
      if (response.ok) {
        const data = await response.json();
        console.log('Backend health data:', data);
        expect(response.status).toBe(200);
      } else {
        console.log('Backend returned error status:', response.status, response.statusText);
        // We'll still consider this a "success" in terms of connectivity
        // The test is to check if we can reach the backend, not if it's healthy
        expect(response.status).toBeDefined();
      }
    } catch (error: any) {
      console.log('Network error when trying to reach backend:', error.message);
      // This indicates a connectivity issue
      // We'll fail the test to highlight the issue
      expect(error).toBeUndefined();
    }
  });

  it('should be able to make an OPTIONS request to the ingest endpoint', async () => {
    // Test if the upload endpoint is accessible
    console.log('Testing ingest endpoint accessibility:', `${config.BACKEND_API_URL}/ingest`);
    
    try {
      const response = await fetch(`${config.BACKEND_API_URL}/ingest`, {
        method: 'OPTIONS',
      });
      
      console.log('Ingest endpoint response status:', response.status);
      
      if (response.ok) {
        console.log('Allowed methods:', response.headers.get('allow'));
        expect(response.status).toBe(200);
      } else {
        console.log('Ingest endpoint returned error status:', response.status, response.statusText);
        // Still consider this a "success" in terms of connectivity
        expect(response.status).toBeDefined();
      }
    } catch (error: any) {
      console.log('Network error when trying to reach ingest endpoint:', error.message);
      // This indicates a connectivity issue
      expect(error).toBeUndefined();
    }
  });
});
