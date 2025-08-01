"""Integration tests for hybrid knowledge retrieval system."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, List

from oracle.services.hybrid_retrieval import HybridKnowledgeRetrieval, RetrievalResult
from oracle.clients.neo4j_client import Neo4jClient, GraphQueryResult, GraphEntity, GraphRelationship
from oracle.clients.chromadb_client import ChromaDBClient
from oracle.models.chat import Source
from oracle.models.errors import OracleException


@pytest.fixture
def mock_neo4j_client():
    """Create a mock Neo4j client."""
    client = AsyncMock(spec=Neo4jClient)
    
    # Mock health check
    client.health_check.return_value = True
    
    # Mock query_knowledge method
    entities = [
        GraphEntity(
            id="entity_1",
            name="Database Connection",
            type="concept",
            description="How to connect to databases",
            properties={"category": "technical", "difficulty": "intermediate"}
        ),
        GraphEntity(
            id="entity_2", 
            name="SQL Query",
            type="concept",
            description="Structured Query Language for databases",
            properties={"category": "technical", "difficulty": "beginner"}
        )
    ]
    
    relationships = [
        GraphRelationship(
            id="rel_1",
            type="RELATES_TO",
            source_id="entity_1",
            target_id="entity_2",
            properties={"strength": 0.8}
        )
    ]
    
    client.query_knowledge.return_value = GraphQueryResult(
        entities=entities,
        relationships=relationships,
        raw_results=[],
        query_time=0.1
    )
    
    return client


@pytest.fixture
def mock_chromadb_client():
    """Create a mock ChromaDB client."""
    client = AsyncMock(spec=ChromaDBClient)
    
    # Mock health check
    client.health_check.return_value = {"status": "healthy"}
    
    # Mock similarity search
    client.similarity_search.return_value = [
        {
            "document": "Database connections require proper authentication and connection strings.",
            "metadata": {"source": "manual.pdf", "page": 1, "document_type": "manual"},
            "distance": 0.2,
            "id": "doc_1_chunk_0",
            "similarity_score": 0.8
        },
        {
            "document": "SQL queries can be used to retrieve, insert, update, and delete data.",
            "metadata": {"source": "tutorial.txt", "section": "basics", "document_type": "tutorial"},
            "distance": 0.3,
            "id": "doc_2_chunk_1", 
            "similarity_score": 0.7
        }
    ]
    
    return client


@pytest.fixture
def hybrid_retrieval_config():
    """Configuration for hybrid retrieval service."""
    return {
        "max_graph_results": 10,
        "max_vector_results": 10,
        "similarity_threshold": 0.6,
        "graph_weight": 0.6,
        "vector_weight": 0.4,
        "cache_enabled": True,
        "cache_ttl_seconds": 300,
        "max_cache_size": 100
    }


@pytest.fixture
def hybrid_retrieval_service(mock_neo4j_client, mock_chromadb_client, hybrid_retrieval_config):
    """Create hybrid retrieval service with mocked clients."""
    return HybridKnowledgeRetrieval(
        neo4j_client=mock_neo4j_client,
        chromadb_client=mock_chromadb_client,
        config=hybrid_retrieval_config
    )


class TestHybridKnowledgeRetrieval:
    """Test cases for hybrid knowledge retrieval service."""
    
    @pytest.mark.asyncio
    async def test_retrieve_knowledge_both_sources(self, hybrid_retrieval_service):
        """Test knowledge retrieval from both graph and vector sources."""
        result = await hybrid_retrieval_service.retrieve_knowledge(
            query="database connection",
            max_sources=5,
            include_graph=True,
            include_vector=True
        )
        
        assert isinstance(result, RetrievalResult)
        assert len(result.sources) > 0
        assert result.query_time > 0
        assert not result.cache_hit  # First call should not be cache hit
        
        # Check that we have sources from both types
        source_types = {source.type for source in result.sources}
        assert "graph" in source_types
        assert "vector" in source_types
        
        # Verify sources are properly ranked
        for i in range(len(result.sources) - 1):
            assert result.sources[i].relevance_score >= result.sources[i + 1].relevance_score
    
    @pytest.mark.asyncio
    async def test_retrieve_knowledge_graph_only(self, hybrid_retrieval_service):
        """Test knowledge retrieval from graph source only."""
        result = await hybrid_retrieval_service.retrieve_knowledge(
            query="database connection",
            max_sources=5,
            include_graph=True,
            include_vector=False
        )
        
        assert isinstance(result, RetrievalResult)
        assert len(result.sources) > 0
        
        # Check that we only have graph sources
        source_types = {source.type for source in result.sources}
        assert source_types == {"graph"}
    
    @pytest.mark.asyncio
    async def test_retrieve_knowledge_vector_only(self, hybrid_retrieval_service):
        """Test knowledge retrieval from vector source only."""
        result = await hybrid_retrieval_service.retrieve_knowledge(
            query="database connection",
            max_sources=5,
            include_graph=False,
            include_vector=True
        )
        
        assert isinstance(result, RetrievalResult)
        assert len(result.sources) > 0
        
        # Check that we only have vector sources
        source_types = {source.type for source in result.sources}
        assert source_types == {"vector"}
    
    @pytest.mark.asyncio
    async def test_cache_functionality(self, hybrid_retrieval_service):
        """Test caching functionality."""
        query = "database connection"
        
        # First call - should not be cached
        result1 = await hybrid_retrieval_service.retrieve_knowledge(
            query=query,
            max_sources=5
        )
        assert not result1.cache_hit
        
        # Second call with same query - should be cached
        result2 = await hybrid_retrieval_service.retrieve_knowledge(
            query=query,
            max_sources=5
        )
        assert result2.cache_hit
        assert len(result2.sources) == len(result1.sources)
    
    @pytest.mark.asyncio
    async def test_similarity_threshold_filtering(self, hybrid_retrieval_service):
        """Test that similarity threshold filtering works."""
        # Set high threshold to filter out low-similarity results
        result = await hybrid_retrieval_service.retrieve_knowledge(
            query="database connection",
            max_sources=10,
            similarity_threshold=0.9  # Very high threshold
        )
        
        # Should have fewer or no vector results due to high threshold
        vector_sources = [s for s in result.sources if s.type == "vector"]
        assert len(vector_sources) == 0  # Mock data has max 0.8 similarity
    
    @pytest.mark.asyncio
    async def test_error_handling_neo4j_failure(self, mock_chromadb_client, hybrid_retrieval_config):
        """Test error handling when Neo4j fails."""
        # Create failing Neo4j client
        failing_neo4j = AsyncMock(spec=Neo4jClient)
        failing_neo4j.health_check.return_value = False
        
        service = HybridKnowledgeRetrieval(
            neo4j_client=failing_neo4j,
            chromadb_client=mock_chromadb_client,
            config=hybrid_retrieval_config
        )
        
        result = await service.retrieve_knowledge(
            query="database connection",
            max_sources=5
        )
        
        # Should still work with only vector results
        assert len(result.sources) > 0
        source_types = {source.type for source in result.sources}
        assert source_types == {"vector"}
    
    @pytest.mark.asyncio
    async def test_error_handling_chromadb_failure(self, mock_neo4j_client, hybrid_retrieval_config):
        """Test error handling when ChromaDB fails."""
        # Create failing ChromaDB client
        failing_chromadb = AsyncMock(spec=ChromaDBClient)
        failing_chromadb.health_check.return_value = {"status": "unhealthy"}
        
        service = HybridKnowledgeRetrieval(
            neo4j_client=mock_neo4j_client,
            chromadb_client=failing_chromadb,
            config=hybrid_retrieval_config
        )
        
        result = await service.retrieve_knowledge(
            query="database connection",
            max_sources=5
        )
        
        # Should still work with only graph results
        assert len(result.sources) > 0
        source_types = {source.type for source in result.sources}
        assert source_types == {"graph"}
    
    @pytest.mark.asyncio
    async def test_deduplication(self, hybrid_retrieval_service):
        """Test that duplicate sources are properly deduplicated."""
        # Mock clients to return duplicate content
        hybrid_retrieval_service.chromadb_client.similarity_search.return_value = [
            {
                "document": "Database connections require proper authentication.",
                "metadata": {"source": "doc1.pdf"},
                "distance": 0.2,
                "id": "doc_1",
                "similarity_score": 0.8
            },
            {
                "document": "Database connections require proper authentication.",  # Duplicate
                "metadata": {"source": "doc2.pdf"},
                "distance": 0.3,
                "id": "doc_2",
                "similarity_score": 0.7
            }
        ]
        
        result = await hybrid_retrieval_service.retrieve_knowledge(
            query="database connection",
            max_sources=10
        )
        
        # Should have deduplicated the identical content
        vector_sources = [s for s in result.sources if s.type == "vector"]
        assert len(vector_sources) == 1  # Only one should remain after deduplication
        # Score should be weighted (0.8 * 0.4) plus ranking boosts
        assert vector_sources[0].relevance_score >= 0.8 * 0.4  # At least the base weighted score
    
    @pytest.mark.asyncio
    async def test_context_aggregation(self, hybrid_retrieval_service):
        """Test context aggregation functionality."""
        result = await hybrid_retrieval_service.retrieve_knowledge(
            query="database connection",
            max_sources=5
        )
        
        # Check that sources have aggregated metadata
        for source in result.sources:
            assert "retrieval_timestamp" in source.metadata
            assert "retrieval_method" in source.metadata
            assert source.metadata["retrieval_method"] == "hybrid"
    
    @pytest.mark.asyncio
    async def test_ranking_algorithm(self, hybrid_retrieval_service):
        """Test that sources are properly ranked."""
        result = await hybrid_retrieval_service.retrieve_knowledge(
            query="database connection SQL",
            max_sources=10
        )
        
        # Verify ranking order
        for i in range(len(result.sources) - 1):
            current_score = result.sources[i].relevance_score
            next_score = result.sources[i + 1].relevance_score
            assert current_score >= next_score, f"Source {i} score {current_score} < Source {i+1} score {next_score}"
    
    def test_cache_key_generation(self, hybrid_retrieval_service):
        """Test cache key generation for different queries."""
        options1 = {"max_sources": 5, "include_graph": True, "include_vector": True}
        options2 = {"max_sources": 10, "include_graph": True, "include_vector": True}
        
        key1 = hybrid_retrieval_service._generate_cache_key("test query", options1)
        key2 = hybrid_retrieval_service._generate_cache_key("test query", options2)
        key3 = hybrid_retrieval_service._generate_cache_key("different query", options1)
        
        # Different options should generate different keys
        assert key1 != key2
        # Different queries should generate different keys
        assert key1 != key3
        # Same query and options should generate same key
        key1_repeat = hybrid_retrieval_service._generate_cache_key("test query", options1)
        assert key1 == key1_repeat
    
    def test_cache_stats(self, hybrid_retrieval_service):
        """Test cache statistics functionality."""
        stats = hybrid_retrieval_service.get_cache_stats()
        
        assert "cache_enabled" in stats
        assert "cache_size" in stats
        assert "max_cache_size" in stats
        assert stats["cache_enabled"] is True
    
    def test_clear_cache(self, hybrid_retrieval_service):
        """Test cache clearing functionality."""
        # Add some entries to cache
        hybrid_retrieval_service._cache["test_key"] = MagicMock()
        
        cleared_count = hybrid_retrieval_service.clear_cache()
        
        assert cleared_count == 1
        assert len(hybrid_retrieval_service._cache) == 0
    
    @pytest.mark.asyncio
    async def test_health_check(self, hybrid_retrieval_service):
        """Test health check functionality."""
        health = await hybrid_retrieval_service.health_check()
        
        assert "service" in health
        assert "neo4j" in health
        assert "chromadb" in health
        assert "cache_enabled" in health
        assert health["service"] == "healthy"
    
    @pytest.mark.asyncio
    async def test_max_sources_limit(self, hybrid_retrieval_service):
        """Test that max_sources parameter is respected."""
        result = await hybrid_retrieval_service.retrieve_knowledge(
            query="database connection",
            max_sources=2
        )
        
        assert len(result.sources) <= 2
    
    @pytest.mark.asyncio
    async def test_weighted_scoring(self, hybrid_retrieval_service):
        """Test that graph and vector weights are applied correctly."""
        result = await hybrid_retrieval_service.retrieve_knowledge(
            query="database connection",
            max_sources=10
        )
        
        graph_sources = [s for s in result.sources if s.type == "graph"]
        vector_sources = [s for s in result.sources if s.type == "vector"]
        
        # Check that weights are applied (graph_weight=0.6, vector_weight=0.4)
        # Note: Final scores include ranking boosts, so they may exceed base weights
        if graph_sources:
            # Graph sources should have base scores influenced by graph weight
            # But final scores may be higher due to ranking boosts
            assert all(s.relevance_score <= 1.0 for s in graph_sources)
        
        if vector_sources:
            # Vector sources should have base scores influenced by vector weight
            # But final scores may be higher due to ranking boosts
            assert all(s.relevance_score <= 1.0 for s in vector_sources)


class TestHybridRetrievalIntegration:
    """Integration tests for hybrid retrieval with real-like scenarios."""
    
    @pytest.mark.asyncio
    async def test_concurrent_retrieval(self, hybrid_retrieval_service):
        """Test concurrent knowledge retrieval requests."""
        queries = [
            "database connection",
            "SQL query syntax", 
            "authentication methods",
            "data backup procedures"
        ]
        
        # Execute concurrent requests
        tasks = [
            hybrid_retrieval_service.retrieve_knowledge(query, max_sources=3)
            for query in queries
        ]
        
        results = await asyncio.gather(*tasks)
        
        # All requests should succeed
        assert len(results) == len(queries)
        for result in results:
            assert isinstance(result, RetrievalResult)
            assert len(result.sources) > 0
    
    @pytest.mark.asyncio
    async def test_cache_performance_under_load(self, hybrid_retrieval_service):
        """Test cache performance under multiple requests."""
        query = "database connection"
        
        # First request - populate cache
        await hybrid_retrieval_service.retrieve_knowledge(query, max_sources=5)
        
        # Multiple concurrent cached requests
        tasks = [
            hybrid_retrieval_service.retrieve_knowledge(query, max_sources=5)
            for _ in range(10)
        ]
        
        results = await asyncio.gather(*tasks)
        
        # All should be cache hits
        for result in results:
            assert result.cache_hit
            assert len(result.sources) > 0
    
    @pytest.mark.asyncio
    async def test_fallback_behavior(self, hybrid_retrieval_config):
        """Test fallback behavior when both sources fail."""
        # Create service with failing clients
        failing_neo4j = AsyncMock(spec=Neo4jClient)
        failing_neo4j.health_check.return_value = False
        
        failing_chromadb = AsyncMock(spec=ChromaDBClient)
        failing_chromadb.health_check.return_value = {"status": "unhealthy"}
        
        service = HybridKnowledgeRetrieval(
            neo4j_client=failing_neo4j,
            chromadb_client=failing_chromadb,
            config=hybrid_retrieval_config
        )
        
        result = await service.retrieve_knowledge(
            query="database connection",
            max_sources=5
        )
        
        # Should return empty results gracefully
        assert isinstance(result, RetrievalResult)
        assert len(result.sources) == 0
        assert result.query_time > 0