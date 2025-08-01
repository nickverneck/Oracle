"""Tests for knowledge retrieval service with vector database integration."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, List

from oracle.services.knowledge import KnowledgeRetrievalService
from oracle.models.chat import Source
from oracle.models.errors import OracleException, ErrorCode


class TestKnowledgeRetrievalService:
    """Test cases for knowledge retrieval service."""
    
    @pytest.fixture
    def mock_chromadb_client(self):
        """Mock ChromaDB client."""
        with patch('oracle.services.knowledge.ChromaDBClient') as mock_client:
            yield mock_client
    
    @pytest.fixture
    def config(self):
        """Test configuration."""
        return {
            "neo4j": {
                "uri": "bolt://localhost:7687",
                "username": "neo4j",
                "password": "password"
            },
            "chromadb": {
                "host": "localhost",
                "port": 8002,
                "embedding_model": "test-model",
                "collection_name": "test_collection"
            },
            "retrieval": {
                "max_graph_results": 5,
                "max_vector_results": 5,
                "similarity_threshold": 0.7
            }
        }
    
    @pytest.fixture
    def knowledge_service(self, config, mock_chromadb_client):
        """Create knowledge service instance."""
        return KnowledgeRetrievalService(config)
    
    def test_init(self, knowledge_service, mock_chromadb_client):
        """Test knowledge service initialization."""
        assert knowledge_service.config is not None
        assert knowledge_service.chromadb_client is not None
        assert knowledge_service._neo4j_available is False
        assert knowledge_service._chromadb_available is False
        
        # Check ChromaDB client was initialized with correct parameters
        mock_chromadb_client.assert_called_once_with(
            host="localhost",
            port=8002,
            embedding_model="test-model",
            collection_name="test_collection"
        )
    
    @pytest.mark.asyncio
    async def test_check_chromadb_availability_success(self, knowledge_service):
        """Test successful ChromaDB availability check."""
        knowledge_service.chromadb_client.health_check = AsyncMock(
            return_value={"status": "healthy"}
        )
        
        await knowledge_service._check_chromadb_availability()
        
        assert knowledge_service._chromadb_available is True
    
    @pytest.mark.asyncio
    async def test_check_chromadb_availability_failure(self, knowledge_service):
        """Test failed ChromaDB availability check."""
        knowledge_service.chromadb_client.health_check = AsyncMock(
            return_value={"status": "unhealthy"}
        )
        
        await knowledge_service._check_chromadb_availability()
        
        assert knowledge_service._chromadb_available is False
    
    @pytest.mark.asyncio
    async def test_check_chromadb_availability_exception(self, knowledge_service):
        """Test ChromaDB availability check with exception."""
        knowledge_service.chromadb_client.health_check = AsyncMock(
            side_effect=Exception("Connection failed")
        )
        
        await knowledge_service._check_chromadb_availability()
        
        assert knowledge_service._chromadb_available is False
    
    @pytest.mark.asyncio
    async def test_retrieve_from_vector_success(self, knowledge_service):
        """Test successful vector retrieval."""
        # Mock ChromaDB search results
        mock_results = [
            {
                'document': 'Test document content',
                'metadata': {'source': 'test.txt'},
                'distance': 0.2,
                'id': 'doc1',
                'similarity_score': 0.8
            },
            {
                'document': 'Another document',
                'metadata': {'source': 'test2.txt'},
                'distance': 0.3,
                'id': 'doc2',
                'similarity_score': 0.7
            }
        ]
        
        knowledge_service.chromadb_client.similarity_search = AsyncMock(
            return_value=mock_results
        )
        
        sources = await knowledge_service._retrieve_from_vector("test query", 5)
        
        assert len(sources) == 2
        assert sources[0].type == "vector"
        assert sources[0].content == "Test document content"
        assert sources[0].relevance_score == 0.8
        # Check that metadata includes both original and ChromaDB-specific fields
        assert sources[0].metadata["source"] == "test.txt"  # Original metadata preserved
        assert sources[0].metadata["source_type"] == "chromadb"  # ChromaDB-specific field
        assert sources[0].metadata["document_id"] == "doc1"
        assert sources[0].metadata["similarity_score"] == 0.8
    
    @pytest.mark.asyncio
    async def test_retrieve_from_vector_with_threshold_filtering(self, knowledge_service):
        """Test vector retrieval with similarity threshold filtering."""
        # Mock ChromaDB search results with varying similarity scores
        mock_results = [
            {
                'document': 'High similarity document',
                'metadata': {'source': 'test1.txt'},
                'distance': 0.2,
                'id': 'doc1',
                'similarity_score': 0.8  # Above threshold
            },
            {
                'document': 'Low similarity document',
                'metadata': {'source': 'test2.txt'},
                'distance': 0.4,
                'id': 'doc2',
                'similarity_score': 0.6  # Below threshold (0.7)
            }
        ]
        
        knowledge_service.chromadb_client.similarity_search = AsyncMock(
            return_value=mock_results
        )
        
        sources = await knowledge_service._retrieve_from_vector("test query", 5)
        
        # Only the high similarity document should be returned
        assert len(sources) == 1
        assert sources[0].content == "High similarity document"
        assert sources[0].relevance_score == 0.8
    
    @pytest.mark.asyncio
    async def test_retrieve_from_vector_exception(self, knowledge_service):
        """Test vector retrieval with exception."""
        knowledge_service.chromadb_client.similarity_search = AsyncMock(
            side_effect=Exception("Search failed")
        )
        
        sources = await knowledge_service._retrieve_from_vector("test query", 5)
        
        # Should return empty list on error for graceful degradation
        assert sources == []
    
    @pytest.mark.asyncio
    async def test_retrieve_knowledge_vector_only(self, knowledge_service):
        """Test knowledge retrieval with only vector database available."""
        knowledge_service._chromadb_available = True
        knowledge_service._neo4j_available = False
        
        # Mock vector retrieval
        mock_vector_sources = [
            Source(
                type="vector",
                content="Vector result",
                relevance_score=0.8,
                metadata={"source": "chromadb"}
            )
        ]
        knowledge_service._retrieve_from_vector = AsyncMock(return_value=mock_vector_sources)
        
        sources = await knowledge_service.retrieve_knowledge("test query")
        
        assert len(sources) == 1
        assert sources[0].type == "vector"
        assert sources[0].content == "Vector result"
    
    @pytest.mark.asyncio
    async def test_retrieve_knowledge_no_sources_available(self, knowledge_service):
        """Test knowledge retrieval when no sources are available."""
        knowledge_service._chromadb_available = False
        knowledge_service._neo4j_available = False
        
        sources = await knowledge_service.retrieve_knowledge("test query")
        
        # Should return placeholder sources
        assert len(sources) > 0
        assert sources[0].metadata.get("source") == "placeholder"
    
    @pytest.mark.asyncio
    async def test_retrieve_knowledge_with_exception_handling(self, knowledge_service):
        """Test knowledge retrieval with exception handling."""
        knowledge_service._chromadb_available = True
        knowledge_service._neo4j_available = False
        
        # Mock vector retrieval to raise exception
        knowledge_service._retrieve_from_vector = AsyncMock(
            side_effect=Exception("Retrieval failed")
        )
        
        sources = await knowledge_service.retrieve_knowledge("test query")
        
        # Should return placeholder sources when all retrievals fail
        assert len(sources) > 0
        assert sources[0].metadata.get("source") == "placeholder"
    
    @pytest.mark.asyncio
    async def test_add_document_to_vector_db_success(self, knowledge_service):
        """Test successful document addition to vector database."""
        knowledge_service.chromadb_client.add_document_chunks = AsyncMock(return_value=5)
        
        text = "Test document content"
        metadata = {"filename": "test.txt", "source": "upload"}
        document_id = "test_doc_123"
        
        chunks_created = await knowledge_service.add_document_to_vector_db(
            text=text,
            metadata=metadata,
            document_id=document_id,
            chunk_size=1000,
            chunk_overlap=200
        )
        
        assert chunks_created == 5
        knowledge_service.chromadb_client.add_document_chunks.assert_called_once_with(
            text=text,
            metadata=metadata,
            document_id=document_id,
            chunk_size=1000,
            chunk_overlap=200
        )
    
    @pytest.mark.asyncio
    async def test_add_document_to_vector_db_failure(self, knowledge_service):
        """Test document addition failure."""
        knowledge_service.chromadb_client.add_document_chunks = AsyncMock(
            side_effect=Exception("Add failed")
        )
        
        with pytest.raises(OracleException) as exc_info:
            await knowledge_service.add_document_to_vector_db(
                text="test",
                metadata={"filename": "test.txt"},
                document_id="test_doc"
            )
        
        assert exc_info.value.error_code == ErrorCode.VECTOR_DB_ERROR
        assert "Failed to add document to vector database" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_get_vector_db_stats_success(self, knowledge_service):
        """Test successful vector database stats retrieval."""
        mock_stats = {
            "name": "test_collection",
            "document_count": 42,
            "embedding_model": "test-model"
        }
        knowledge_service.chromadb_client.get_collection_stats = AsyncMock(
            return_value=mock_stats
        )
        
        stats = await knowledge_service.get_vector_db_stats()
        
        assert stats == mock_stats
    
    @pytest.mark.asyncio
    async def test_get_vector_db_stats_failure(self, knowledge_service):
        """Test vector database stats retrieval failure."""
        knowledge_service.chromadb_client.get_collection_stats = AsyncMock(
            side_effect=Exception("Stats failed")
        )
        
        stats = await knowledge_service.get_vector_db_stats()
        
        assert "error" in stats
        assert "Stats failed" in stats["error"]
    
    @pytest.mark.asyncio
    async def test_health_check(self, knowledge_service):
        """Test health check."""
        knowledge_service._neo4j_available = False
        knowledge_service._chromadb_available = True
        
        health = await knowledge_service.health_check()
        
        assert health["neo4j"] is False
        assert health["chromadb"] is True
        assert health["knowledge_service"] is True
    
    def test_get_retrieval_stats(self, knowledge_service):
        """Test retrieval statistics."""
        knowledge_service._neo4j_available = False
        knowledge_service._chromadb_available = True
        
        stats = knowledge_service.get_retrieval_stats()
        
        assert stats["neo4j_available"] is False
        assert stats["chromadb_available"] is True
        assert stats["config"]["max_graph_results"] == 5
        assert stats["config"]["max_vector_results"] == 5
        assert stats["config"]["similarity_threshold"] == 0.7