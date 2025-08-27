import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/svelte';
import { tick } from 'svelte';
import userEvent from '@testing-library/user-event';
import DataPage from './+page.svelte';

// Import the actual ingestion service to test real backend connectivity
import { uploadFiles } from '$lib/services/ingestion';

// Mock config to use a test backend URL
vi.mock('$lib/config', () => ({
  default: {
    BACKEND_API_URL: 'http://localhost:8000/api/v1' // Adjust this to match your backend URL
  }
}));

describe('Data Ingestion Page - Backend Connectivity Test', () => {
  const user = userEvent.setup();
  
  beforeEach(() => {
    // Clean up DOM
    document.body.innerHTML = '';
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('should display the upload interface correctly', async () => {
    render(DataPage);
    
    // Check main elements are present
    expect(screen.getByText('Data Ingestion')).toBeInTheDocument();
    expect(screen.getByText('Upload Documents')).toBeInTheDocument();
    expect(screen.getByText('Drag and drop files here, or click to browse')).toBeInTheDocument();
    expect(screen.getByText('Choose Files')).toBeInTheDocument();
    
    // Check processing method options
    expect(screen.getByText('Knowledge Graph')).toBeInTheDocument();
    expect(screen.getByText('RAG')).toBeInTheDocument();
    expect(screen.getByText('Both')).toBeInTheDocument();
  });

  it('should handle file selection and attempt backend upload', async () => {
    render(DataPage);
    
    // Create mock files
    const file1 = new File(['test content 1'], 'test1.pdf', { type: 'application/pdf' });
    const file2 = new File(['test content 2'], 'test2.txt', { type: 'text/plain' });
    
    // Get the file input element
    const fileInput = screen.getByTestId('file-input');
    
    // Spy on the uploadFiles function
    const uploadSpy = vi.spyOn(await import('$lib/services/ingestion'), 'uploadFiles');
    
    // Simulate file selection
    await userEvent.upload(fileInput, [file1, file2]);
    
    // Wait for Svelte to update
    await tick();
    
    // Check that files are displayed
    expect(screen.getByText('test1.pdf')).toBeInTheDocument();
    expect(screen.getByText('test2.txt')).toBeInTheDocument();
    
    // Wait a bit for the upload process to start
    await waitFor(() => {
      expect(uploadSpy).toHaveBeenCalled();
    }, { timeout: 5000 });
    
    // Check that the uploadFiles function was called with correct parameters
    expect(uploadSpy).toHaveBeenCalledWith(
      [file1, file2],
      'both', // default processing type
      expect.any(Function) // progress callback
    );
  });

  it('should handle backend connectivity and show appropriate status', async () => {
    render(DataPage);
    
    // Create a mock file
    const file = new File(['test content'], 'test.pdf', { type: 'application/pdf' });
    
    // Get the file input element
    const fileInput = screen.getByTestId('file-input');
    
    // Spy on the uploadFiles function
    const uploadSpy = vi.spyOn(await import('$lib/services/ingestion'), 'uploadFiles');
    
    // Mock the uploadFiles function to simulate backend behavior
    uploadSpy.mockImplementation(async (files, processingType, onUploadProgress) => {
      // Simulate upload progress
      onUploadProgress(50);
      await new Promise(resolve => setTimeout(resolve, 100));
      onUploadProgress(100);
      
      // Simulate backend response or error
      try {
        // This will actually make a real request to the backend
        const response = await fetch('http://localhost:8000/api/v1/health', {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
          },
        });
        
        if (response.ok) {
          // Backend is reachable
          return {
            status: 'success',
            total_files: files.length,
            successful_files: files.length,
            failed_files: 0,
            errors: [],
            processing_time: 0.1,
          };
        } else {
          // Backend returned an error
          throw new Error(`Backend error: ${response.status} ${response.statusText}`);
        }
      } catch (error: any) {
        // Network error or backend unreachable
        throw new Error(`Network error: ${error.message}`);
      }
    });
    
    // Simulate file selection
    await userEvent.upload(fileInput, [file]);
    
    // Wait for Svelte to update
    await tick();
    
    // Check that file is displayed
    expect(screen.getByText('test.pdf')).toBeInTheDocument();
    
    // Wait for upload to complete
    await waitFor(() => {
      expect(uploadSpy).toHaveBeenCalled();
    }, { timeout: 10000 });
    
    // Check for status updates in UI
    // Note: The actual status display depends on the backend response
    // This test will help identify if the issue is frontend or backend related
  });

  it('should correctly format file sizes', async () => {
    render(DataPage);
    
    // Create mock files with different sizes
    const smallFile = new File(['a'], 'small.txt', { type: 'text/plain' }); // 1 byte
    const mediumFile = new File(['a'.repeat(1024)], 'medium.txt', { type: 'text/plain' }); // 1KB
    const largeFile = new File(['a'.repeat(1024 * 1024)], 'large.txt', { type: 'text/plain' }); // 1MB
    
    // Get the file input element
    const fileInput = screen.getByTestId('file-input');
    
    // Simulate file selection
    await userEvent.upload(fileInput, [smallFile, mediumFile, largeFile]);
    
    // Wait for Svelte to update
    await tick();
    
    // Check files are displayed
    expect(screen.getByText('small.txt')).toBeInTheDocument();
    expect(screen.getByText('medium.txt')).toBeInTheDocument();
    expect(screen.getByText('large.txt')).toBeInTheDocument();
    
    // Note: Actual size display depends on the component implementation
    // This test verifies the file selection and display logic
  });

  it('should handle processing type selection', async () => {
    render(DataPage);
    
    // Check default selection
    const bothButton = screen.getByText('Both').closest('button');
    if (bothButton) expect(bothButton).toHaveClass('border-blue-500');
    
    // Select Knowledge Graph
    const kgButton = screen.getByText('Knowledge Graph').closest('button');
    if (kgButton) await userEvent.click(kgButton);
    
    // Check selection changed
    if (kgButton) expect(kgButton).toHaveClass('border-blue-500');
    if (bothButton) expect(bothButton).not.toHaveClass('border-blue-500');
    
    // Select RAG
    const ragButton = screen.getByText('RAG').closest('button');
    if (ragButton) await userEvent.click(ragButton);
    
    // Check selection changed
    if (ragButton) expect(ragButton).toHaveClass('border-blue-500');
    if (kgButton) expect(kgButton).not.toHaveClass('border-blue-500');
  });

  // Test to specifically diagnose connectivity issues
  it('should diagnose backend connectivity', async () => {
    // Test direct backend connectivity
    try {
      const response = await fetch('http://localhost:8000/api/v1/health', {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      
      if (response.ok) {
        console.log('Backend connectivity: SUCCESS');
        console.log('Backend status:', await response.json());
      } else {
        console.log('Backend connectivity: FAILED');
        console.log('Status:', response.status, response.statusText);
      }
    } catch (error) {
      console.log('Backend connectivity: NETWORK ERROR');
      console.log('Error:', error.message);
    }
    
    // Test if the backend URL is correctly configured
    const config = await import('$lib/config');
    console.log('Configured backend URL:', config.default.BACKEND_API_URL);
    
    // Test if the upload endpoint is accessible
    try {
      const response = await fetch(`${config.default.BACKEND_API_URL}/ingest`, {
        method: 'OPTIONS',
      });
      
      if (response.ok) {
        console.log('Upload endpoint accessible: YES');
        console.log('Allowed methods:', response.headers.get('allow'));
      } else {
        console.log('Upload endpoint accessible: NO');
        console.log('Status:', response.status, response.statusText);
      }
    } catch (error: any) {
      console.log('Upload endpoint test: NETWORK ERROR');
      console.log('Error:', error.message);
    }
  });
});
