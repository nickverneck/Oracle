// Environment configuration
const config = {
    // Backend API URL - defaults to relative path for same-origin requests
    // In Docker, this will be set via BACKEND_URL environment variable
    BACKEND_API_URL: import.meta.env.VITE_BACKEND_URL || '/api/v1'
};

export default config;
