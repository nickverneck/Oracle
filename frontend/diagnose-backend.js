// Simple diagnostic script to check backend connectivity
// Run this in the browser console or as a Node.js script

// Configuration
const BACKEND_API_URL = '/api/v1'; // Default value from config.ts

console.log('Backend Diagnostic Script');
console.log('========================');
console.log('Backend API URL:', BACKEND_API_URL);

// Check if we're running in a browser environment
if (typeof window !== 'undefined' && typeof fetch !== 'undefined') {
  console.log('\nRunning in browser environment');
  
  // Test health endpoint
  console.log('\n1. Testing health endpoint...');
  fetch(BACKEND_API_URL + '/health', {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    }
  })
  .then(response => {
    console.log('   Status:', response.status, response.statusText);
    if (response.ok) {
      return response.json();
    } else {
      console.log('   Error: Response not OK');
      return null;
    }
  })
  .then(data => {
    if (data) {
      console.log('   Data:', data);
    }
  })
  .catch(error => {
    console.log('   Error:', error.name, error.message);
  });
  
  // Test ingest endpoint OPTIONS
  console.log('\n2. Testing ingest endpoint OPTIONS...');
  fetch(BACKEND_API_URL + '/ingest', {
    method: 'OPTIONS'
  })
  .then(response => {
    console.log('   Status:', response.status, response.statusText);
    if (response.ok) {
      console.log('   Allowed methods:', response.headers.get('allow'));
    }
  })
  .catch(error => {
    console.log('   Error:', error.name, error.message);
  });
  
  // Test actual POST request (will fail without files)
  console.log('\n3. Testing ingest endpoint POST (expected to fail without files)...');
  fetch(BACKEND_API_URL + '/ingest', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ test: 'data' })
  })
  .then(response => {
    console.log('   Status:', response.status, response.statusText);
  })
  .catch(error => {
    console.log('   Error:', error.name, error.message);
  });
  
} else {
  console.log('\nRunning in Node.js environment');
  console.log('This script is meant to be run in a browser environment to test actual connectivity.');
}
