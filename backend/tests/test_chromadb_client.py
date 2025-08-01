"""Tests for ChromaDB client."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, List

from oracle.clients.chromadb_client import ChromaDBClient
from oracle.models.errors import OracleException, ErrorCode


class TestChromaDBClient:
    """Test cases for ChromaDB client."""
    
    @pytest.fixture
    def mock_chromadb_client(self):
        """Mock ChromaDB client."""
        with patch('oracle.clients.chromadb_client.chromadb.HttpClient') as mock_client:
            yield mock_client
    
    @pytest.fixture
    def mock_embedding_function(self):
        """Mock embedding function."""
        with patch('oracle.clients.chromadb_client.embedding_functions.SentenceTransformerEmbeddingFunction') as mock_func:
            yield mock_func
    
    @pytest.fixture
    def chromadb_client(self, mock_chromadb_client, mock_embedding_function):
        """Create ChromaDB client instance."""
        return ChromaDBClient(
            host="localhost",
            port=8002,
            embedding_model="test-model",
            collection_name="test_collection"
        )
    
    def test_init(self, chromadb_client):
        """Test ChromaDB client initialization."""
        assert chromadb_client.host == "localhost"
        assert chromadb_client.port == 8002
        assert chromadb_client.embedding_model_name == "test-model"
        assert chromadb_client.collection_name == "test_collection"
    
    @pytest.mark.asyncio
    async def test_health_check_success(self, chromadb_client):
        """Test successful health check."""
        # Mock the client methods
        chromadb_client.client.heartbeat = MagicMock(return_value={"status": "ok"})
        chromadb_client.client.list_collections = MagicMock(return_value=[])
        
        health = await chromadb_client.health_check()
        
        assert health["status"] == "healthy"
        assert health["heartbeat"] == {"status": "ok"}
        assert health["collections_count"] == 0
        assert health["embedding_model"] == "test-model"
    
    @pytest.mark.asyncio
    async def test_health_check_failure(self, chromadb_client):
        """Test health check failure."""
        # Mock the client to raise an exception
        chromadb_client.client.heartbeat = MagicMock(side_effect=Exception("Connection failed"))
        
        health = await chromadb_client.health_check()
        
        assert health["status"] == "unhealthy"
        assert "Connection failed" in health["error"]
    
    @pytest.mark.asyncio
    async def test_create_collection_success(self, chromadb_client):
        """Test successful collection creation."""
        chromadb_client.client.create_collection = MagicMock()
        
        result = await chromadb_client.create_collection("test_collection")
        
        assert result is True
        chromadb_client.client.create_collection.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_collection_failure(self, chromadb_client):
        """Test collection creation failure."""
        chromadb_client.client.create_collection = MagicMock(side_effect=Exception("Creation failed"))
        
        result = await chromadb_client.create_collection("test_collection")
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_get_or_create_collection_success(self, chromadb_client):
        """Test successful get or create collection."""
        mock_collection = MagicMock()
        chromadb_client.client.get_or_create_collection = MagicMock(return_value=mock_collection)
        
        collection = await chromadb_client.get_or_create_collection("test_collection")
        
        assert collection == mock_collection
        chromadb_client.client.get_or_create_collection.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_or_create_collection_failure(self, chromadb_client):
        """Test get or create collection failure."""
        chromadb_client.client.get_or_create_collection = MagicMock(side_effect=Exception("Access failed"))
        
        with pytest.raises(OracleException) as exc_info:
            await chromadb_client.get_or_create_collection("test_collection")
        
        assert exc_info.value.error_code == ErrorCode.VECTOR_DB_ERROR
        assert "Failed to access collection" in str(exc_info.value)
    
    def test_chunk_text_small_text(self, chromadb_client):
        """Test chunking small text that doesn't need splitting."""
        text = "This is a small text."
        chunks = chromadb_client.chunk_text(text, chunk_size=100)
        
        assert len(chunks) == 1
        assert chunks[0] == text
    
    def test_chunk_text_large_text(self, chromadb_client):
        """Test chunking large text."""
        text = "This is a sentence. " * 100  # Create long text
        chunks = chromadb_client.chunk_text(text, chunk_size=100, chunk_overlap=20)
        
        assert len(chunks) > 1
        assert all(len(chunk) <= 120 for chunk in chunks)  # Allow for sentence boundary
    
    def test_chunk_text_with_sentence_boundaries(self, chromadb_client):
        """Test chunking respects sentence boundaries."""
        text = "First sentence. Second sentence. Third sentence. Fourth sentence."
        chunks = chromadb_client.chunk_text(text, chunk_size=30, chunk_overlap=5)
        
        # Should break at sentence boundaries when possible
        assert len(chunks) > 1
        assert any(chunk.endswith('.') for chunk in chunks[:-1])
    
    @pytest.mark.asyncio
    async def test_add_documents_success(self, chromadb_client):
        """Test successful document addition."""
        mock_collection = MagicMock()
        chromadb_client.get_or_create_collection = AsyncMock(return_value=mock_collection)
        
        documents = ["doc1", "doc2"]
        metadatas = [{"id": 1}, {"id": 2}]
        ids = ["id1", "id2"]
        
        result = await chromadb_client.add_documents(documents, metadatas, ids)
        
        assert result == 2
        mock_collection.add.assert_called_once_with(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
    
    @pytest.mark.asyncio
    async def test_add_documents_validation_error(self, chromadb_client):
        """Test document addition with validation error."""
        documents = ["doc1"]
        metadatas = [{"id": 1}, {"id": 2}]  # Mismatched length
        ids = ["id1"]
        
        with pytest.raises(ValueError) as exc_info:
            await chromadb_client.add_documents(documents, metadatas, ids)
        
        assert "same length" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_add_documents_chromadb_error(self, chromadb_client):
        """Test document addition with ChromaDB error."""
        mock_collection = MagicMock()
        mock_collection.add = MagicMock(side_effect=Exception("Add failed"))
        chromadb_client.get_or_create_collection = AsyncMock(return_value=mock_collection)
        
        documents = ["doc1"]
        metadatas = [{"id": 1}]
        ids = ["id1"]
        
        with pytest.raises(OracleException) as exc_info:
            await chromadb_client.add_documents(documents, metadatas, ids)
        
        assert exc_info.value.error_code == ErrorCode.VECTOR_DB_ERROR
        assert "Failed to add documents" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_add_document_chunks_success(self, chromadb_client):
        """Test successful document chunking and addition."""
        chromadb_client.add_documents = AsyncMock(return_value=3)
        
        text = "This is a test document. It has multiple sentences. Each will be processed."
        metadata = {"source": "test"}
        document_id = "test_doc"
        
        result = await chromadb_client.add_document_chunks(
            text=text,
            metadata=metadata,
            document_id=document_id,
            chunk_size=50,
            chunk_overlap=10
        )
        
        assert result > 0  # Should create at least one chunk
        chromadb_client.add_documents.assert_called_once()
        
        # Check the call arguments
        call_args = chromadb_client.add_documents.call_args
        assert len(call_args[1]["documents"]) > 0  # Should have chunks
        assert all("chunk_index" in meta for meta in call_args[1]["metadatas"])
        assert all(doc_id.startswith("test_doc_chunk_") for doc_id in call_args[1]["ids"])
    
    @pytest.mark.asyncio
    async def test_add_document_chunks_empty_text(self, chromadb_client):
        """Test document chunking with empty text."""
        result = await chromadb_client.add_document_chunks(
            text="",
            metadata={"source": "test"},
            document_id="test_doc"
        )
        
        assert result == 0
    
    @pytest.mark.asyncio
    async def test_similarity_search_success(self, chromadb_client):
        """Test successful similarity search."""
        mock_collection = MagicMock()
        mock_results = {
            'documents': [['doc1', 'doc2']],
            'metadatas': [[{'source': 'test1'}, {'source': 'test2'}]],
            'distances': [[0.1, 0.2]],
            'ids': [['id1', 'id2']]
        }
        mock_collection.query = MagicMock(return_value=mock_results)
        chromadb_client.get_or_create_collection = AsyncMock(return_value=mock_collection)
        
        results = await chromadb_client.similarity_search("test query", n_results=2)
        
        assert len(results) == 2
        assert results[0]['document'] == 'doc1'
        assert results[0]['metadata'] == {'source': 'test1'}
        assert results[0]['distance'] == 0.1
        assert results[0]['similarity_score'] == 0.9  # 1.0 - 0.1
        assert results[0]['id'] == 'id1'
    
    @pytest.mark.asyncio
    async def test_similarity_search_empty_results(self, chromadb_client):
        """Test similarity search with empty results."""
        mock_collection = MagicMock()
        mock_results = {
            'documents': [[]],
            'metadatas': [[]],
            'distances': [[]],
            'ids': [[]]
        }
        mock_collection.query = MagicMock(return_value=mock_results)
        chromadb_client.get_or_create_collection = AsyncMock(return_value=mock_collection)
        
        results = await chromadb_client.similarity_search("test query")
        
        assert len(results) == 0
    
    @pytest.mark.asyncio
    async def test_similarity_search_failure(self, chromadb_client):
        """Test similarity search failure."""
        chromadb_client.get_or_create_collection = AsyncMock(side_effect=Exception("Search failed"))
        
        with pytest.raises(OracleException) as exc_info:
            await chromadb_client.similarity_search("test query")
        
        assert exc_info.value.error_code == ErrorCode.VECTOR_DB_ERROR
        assert "Similarity search failed" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_delete_documents_success(self, chromadb_client):
        """Test successful document deletion."""
        mock_collection = MagicMock()
        chromadb_client.get_or_create_collection = AsyncMock(return_value=mock_collection)
        
        result = await chromadb_client.delete_documents(["id1", "id2"])
        
        assert result is True
        mock_collection.delete.assert_called_once_with(ids=["id1", "id2"])
    
    @pytest.mark.asyncio
    async def test_delete_documents_failure(self, chromadb_client):
        """Test document deletion failure."""
        mock_collection = MagicMock()
        mock_collection.delete = MagicMock(side_effect=Exception("Delete failed"))
        chromadb_client.get_or_create_collection = AsyncMock(return_value=mock_collection)
        
        result = await chromadb_client.delete_documents(["id1", "id2"])
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_get_collection_stats_success(self, chromadb_client):
        """Test successful collection stats retrieval."""
        mock_collection = MagicMock()
        mock_collection.count = MagicMock(return_value=42)
        chromadb_client.get_or_create_collection = AsyncMock(return_value=mock_collection)
        
        stats = await chromadb_client.get_collection_stats()
        
        assert stats["name"] == "test_collection"
        assert stats["document_count"] == 42
        assert stats["embedding_model"] == "test-model"
    
    @pytest.mark.asyncio
    async def test_get_collection_stats_failure(self, chromadb_client):
        """Test collection stats retrieval failure."""
        chromadb_client.get_or_create_collection = AsyncMock(side_effect=Exception("Stats failed"))
        
        stats = await chromadb_client.get_collection_stats()
        
        assert stats["name"] == "test_collection"
        assert stats["document_count"] == 0
        assert "error" in stats
    
    def test_generate_document_id(self, chromadb_client):
        """Test document ID generation."""
        content = "Test document content"
        metadata = {"filename": "test.txt", "source": "upload"}
        
        doc_id = chromadb_client.generate_document_id(content, metadata)
        
        assert isinstance(doc_id, str)
        assert len(doc_id) == 32  # MD5 hash length
        
        # Same content and metadata should generate same ID
        doc_id2 = chromadb_client.generate_document_id(content, metadata)
        assert doc_id == doc_id2
        
        # Different content should generate different ID
        doc_id3 = chromadb_client.generate_document_id("Different content", metadata)
        assert doc_id != doc_id3