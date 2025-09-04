# Development Dockerfile with hot reloading
FROM node:20-alpine

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apk add --no-cache curl

# Copy package files
COPY package.json package-lock.json* ./

# Install all dependencies (including dev)
RUN npm ci

# Copy application code
COPY . .

# Create non-root user for security
RUN addgroup -g 1001 -S nodejs
RUN adduser -S sveltekit -u 1001
RUN chown -R sveltekit:nodejs /app
USER sveltekit

# Expose ports (3000 for production, 5173 for dev server)
EXPOSE 3000 5173

# Start development server with hot reloading
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]