# Requirements Document

## Introduction

Oracle is a proprietary knowledge-based chatbot system designed to help clients troubleshoot products using advanced AI capabilities. The system combines multiple AI approaches including knowledge graphs, vector databases for RAG (Retrieval-Augmented Generation), and flexible model serving options. The architecture prioritizes ease of deployment through Docker containerization and supports graceful degradation across different AI model providers.

## Requirements

### Requirement 1

**User Story:** As a system administrator, I want to deploy the entire Oracle system using Docker Compose, so that I can quickly set up the system without complex configuration steps.

#### Acceptance Criteria

1. WHEN a user runs docker-compose up THEN the system SHALL start all required services including backend API, frontend, model serving, knowledge graph, and vector database
2. WHEN the system starts THEN it SHALL automatically configure networking between all containers
3. WHEN the system is deployed THEN it SHALL expose the frontend on a configurable port
4. WHEN the system is deployed THEN it SHALL expose the backend API on a configurable port

### Requirement 2

**User Story:** As a client, I want to send chat prompts to get troubleshooting assistance, so that I can resolve product issues efficiently.

#### Acceptance Criteria

1. WHEN a client sends a POST request to the chat endpoint THEN the system SHALL process the prompt using the available AI model
2. WHEN processing a prompt THEN the system SHALL retrieve relevant context from both the knowledge graph and vector database
3. WHEN the AI model is unavailable THEN the system SHALL gracefully degrade to alternative model providers (Ollama or Google Gemini)
4. WHEN a response is generated THEN the system SHALL return structured JSON with the answer and confidence metrics

### Requirement 3

**User Story:** As a content manager, I want to upload documents for knowledge ingestion, so that the system can provide accurate troubleshooting information based on our proprietary knowledge.

#### Acceptance Criteria

1. WHEN a user uploads documents via the ingestion endpoint THEN the system SHALL accept multiple file formats (PDF, TXT, DOCX)
2. WHEN documents are uploaded THEN the system SHALL process them for both knowledge graph and vector database storage
3. WHEN processing documents THEN the system SHALL extract entities and relationships for the knowledge graph
4. WHEN processing documents THEN the system SHALL create embeddings and store them in ChromaDB
5. WHEN ingestion fails THEN the system SHALL return detailed error messages with retry guidance

### Requirement 4

**User Story:** As a developer, I want the backend to use modern Python tooling and FastAPI, so that the system is maintainable and performant.

#### Acceptance Criteria

1. WHEN the backend starts THEN it SHALL use UV for Python package management
2. WHEN API requests are made THEN FastAPI SHALL handle routing and validation
3. WHEN the system serves requests THEN it SHALL provide automatic API documentation via Swagger/OpenAPI
4. WHEN errors occur THEN the system SHALL return appropriate HTTP status codes and error messages

### Requirement 5

**User Story:** As a system operator, I want primary model serving through vLLM with CUDA support, so that I can achieve optimal inference performance.

#### Acceptance Criteria

1. WHEN the system starts THEN vLLM SHALL be configured with CUDA support for GPU acceleration
2. WHEN vLLM is available THEN it SHALL be the primary model serving backend
3. WHEN vLLM fails or is unavailable THEN the system SHALL automatically fallback to Ollama
4. WHEN both vLLM and Ollama are unavailable THEN the system SHALL fallback to Google Gemini API
5. WHEN using any model provider THEN the system SHALL maintain consistent API interfaces

### Requirement 6

**User Story:** As a system architect, I want a hybrid knowledge retrieval approach using both knowledge graphs and vector databases, so that the system can provide comprehensive and contextually relevant responses.

#### Acceptance Criteria

1. WHEN processing queries THEN the system SHALL query both Neo4j knowledge graph and ChromaDB vector database
2. WHEN retrieving from knowledge graph THEN the system SHALL find related entities and relationships
3. WHEN retrieving from vector database THEN the system SHALL perform semantic similarity search
4. WHEN combining results THEN the system SHALL merge and rank information from both sources
5. WHEN knowledge sources are unavailable THEN the system SHALL continue operating with available sources

### Requirement 7

**User Story:** As a frontend developer, I want a SvelteKit 5 frontend container, so that I can build a modern user interface for the chatbot system.

#### Acceptance Criteria

1. WHEN the frontend container starts THEN it SHALL serve a SvelteKit 5 application
2. WHEN the frontend loads THEN it SHALL connect to the backend API endpoints
3. WHEN users interact with the chat interface THEN it SHALL send requests to the backend and display responses
4. WHEN users want to upload documents THEN the frontend SHALL provide an intuitive upload interface
5. WHEN the backend is unavailable THEN the frontend SHALL display appropriate error messages

### Requirement 8

**User Story:** As a DevOps engineer, I want all services to be self-hosted and containerized, so that the system can run in isolated environments without external dependencies.

#### Acceptance Criteria

1. WHEN the system deploys THEN Neo4j SHALL run as a self-hosted container
2. WHEN the system deploys THEN ChromaDB SHALL run as a self-hosted container  
3. WHEN the system deploys THEN all containers SHALL use persistent volumes for data storage
4. WHEN containers restart THEN all data SHALL persist across restarts
5. WHEN the system scales THEN containers SHALL be able to communicate through Docker networks