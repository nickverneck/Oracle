"""Unit tests for Neo4j client."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any

from oracle.clients.neo4j_client import (
    Neo4jClient,
    Neo4jClientError,
    GraphEntity,
    GraphRelationship,
    GraphQueryResult,
    get_neo4j_client,
    close_neo4j_client
)


class TestNeo4jClient:
    """Test cases for Neo4jClient."""
    
    @pytest.fixture
    def mock_config(self) -> Dict[str, Any]:
        """Mock configuration for testing."""
        return {
            "uri": "bolt://localhost:7687",
            "username": "neo4j",
            "password": "test_password"
        }
    
    @pytest.fixture
    def neo4j_client(self, mock_config: Dict[str, Any]) -> Neo4jClient:
        """Create a Neo4jClient instance for testing."""
        return Neo4jClient(mock_config)
    
    @pytest.fixture
    def mock_driver(self):
        """Mock Neo4j driver."""
        driver = AsyncMock()
        driver.verify_connectivity = AsyncMock()
        driver.close = AsyncMock()
        return driver
    
    @pytest.fixture
    def mock_session(self):
        """Mock Neo4j session."""
        session = AsyncMock()
        session.close = AsyncMock()
        return session
    
    @pytest.fixture
    def mock_result(self):
        """Mock Neo4j query result."""
        result = AsyncMock()
        return result
    
    @pytest.mark.asyncio
    async def test_connect_success(self, neo4j_client: Neo4jClient, mock_driver):
        """Test successful connection to Neo4j."""
        with patch('oracle.clients.neo4j_client.AsyncGraphDatabase.driver', return_value=mock_driver):
            await neo4j_client.connect()
            
            assert neo4j_client.driver == mock_driver
            mock_driver.verify_connectivity.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_connect_auth_error(self, neo4j_client: Neo4jClient):
        """Test connection failure due to authentication error."""
        from neo4j.exceptions import AuthError
        
        with patch('oracle.clients.neo4j_client.AsyncGraphDatabase.driver') as mock_driver_class:
            mock_driver_class.return_value.verify_connectivity.side_effect = AuthError("Invalid credentials")
            
            with pytest.raises(Neo4jClientError, match="Authentication failed"):
                await neo4j_client.connect()
    
    @pytest.mark.asyncio
    async def test_connect_service_unavailable(self, neo4j_client: Neo4jClient):
        """Test connection failure due to service unavailable."""
        from neo4j.exceptions import ServiceUnavailable
        
        with patch('oracle.clients.neo4j_client.AsyncGraphDatabase.driver') as mock_driver_class:
            mock_driver_class.return_value.verify_connectivity.side_effect = ServiceUnavailable("Service unavailable")
            
            with pytest.raises(Neo4jClientError, match="Service unavailable"):
                await neo4j_client.connect()
    
    @pytest.mark.asyncio
    async def test_disconnect(self, neo4j_client: Neo4jClient, mock_driver):
        """Test disconnection from Neo4j."""
        neo4j_client.driver = mock_driver
        
        await neo4j_client.disconnect()
        
        mock_driver.close.assert_called_once()
        assert neo4j_client.driver is None
    
    @pytest.mark.asyncio
    async def test_health_check_success(self, neo4j_client: Neo4jClient, mock_driver, mock_session):
        """Test successful health check."""
        neo4j_client.driver = mock_driver
        mock_driver.session.return_value = mock_session
        
        mock_result = AsyncMock()
        mock_record = {"health": 1}
        mock_result.single.return_value = mock_record
        mock_session.run.return_value = mock_result
        
        with patch.object(neo4j_client, 'get_session') as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = mock_session
            mock_get_session.return_value.__aexit__.return_value = None
            
            result = await neo4j_client.health_check()
            
            assert result is True
            mock_session.run.assert_called_once_with("RETURN 1 as health")
    
    @pytest.mark.asyncio
    async def test_health_check_failure(self, neo4j_client: Neo4jClient):
        """Test health check failure."""
        neo4j_client.driver = None
        
        with patch.object(neo4j_client, 'connect', side_effect=Exception("Connection failed")):
            result = await neo4j_client.health_check()
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_create_entity_success(self, neo4j_client: Neo4jClient, mock_session):
        """Test successful entity creation."""
        neo4j_client.driver = AsyncMock()
        
        mock_result = AsyncMock()
        mock_node = {
            "id": "test_entity_1",
            "name": "Test Entity",
            "type": "TEST",
            "description": "A test entity"
        }
        mock_record = {"e": mock_node}
        mock_result.single.return_value = mock_record
        mock_session.run.return_value = mock_result
        
        with patch.object(neo4j_client, 'get_session') as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = mock_session
            mock_get_session.return_value.__aexit__.return_value = None
            
            entity = await neo4j_client.create_entity(
                entity_id="test_entity_1",
                name="Test Entity",
                entity_type="TEST",
                description="A test entity"
            )
            
            assert isinstance(entity, GraphEntity)
            assert entity.id == "test_entity_1"
            assert entity.name == "Test Entity"
            assert entity.type == "TEST"
            assert entity.description == "A test entity"
    
    @pytest.mark.asyncio
    async def test_create_entity_failure(self, neo4j_client: Neo4jClient, mock_session):
        """Test entity creation failure."""
        neo4j_client.driver = AsyncMock()
        
        mock_result = AsyncMock()
        mock_result.single.return_value = None
        mock_session.run.return_value = mock_result
        
        with patch.object(neo4j_client, 'get_session') as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = mock_session
            mock_get_session.return_value.__aexit__.return_value = None
            
            with pytest.raises(Neo4jClientError, match="Failed to create entity"):
                await neo4j_client.create_entity(
                    entity_id="test_entity_1",
                    name="Test Entity",
                    entity_type="TEST"
                )
    
    @pytest.mark.asyncio
    async def test_create_relationship_success(self, neo4j_client: Neo4jClient, mock_session):
        """Test successful relationship creation."""
        neo4j_client.driver = AsyncMock()
        
        mock_result = AsyncMock()
        mock_relationship = {"created_at": "2024-01-01T00:00:00Z"}
        mock_record = {"r": mock_relationship, "rel_id": 123}
        mock_result.single.return_value = mock_record
        mock_session.run.return_value = mock_result
        
        with patch.object(neo4j_client, 'get_session') as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = mock_session
            mock_get_session.return_value.__aexit__.return_value = None
            
            relationship = await neo4j_client.create_relationship(
                source_id="entity_1",
                target_id="entity_2",
                relationship_type="RELATES_TO"
            )
            
            assert isinstance(relationship, GraphRelationship)
            assert relationship.id == "123"
            assert relationship.type == "RELATES_TO"
            assert relationship.source_id == "entity_1"
            assert relationship.target_id == "entity_2"
    
    @pytest.mark.asyncio
    async def test_find_entities_by_name(self, neo4j_client: Neo4jClient, mock_session):
        """Test finding entities by name."""
        neo4j_client.driver = AsyncMock()
        
        mock_result = AsyncMock()
        mock_entities = [
            {"id": "1", "name": "Test Entity 1", "type": "TEST", "description": "First test entity"},
            {"id": "2", "name": "Test Entity 2", "type": "TEST", "description": "Second test entity"}
        ]
        
        async def mock_async_iter(self):
            for entity in mock_entities:
                yield {"e": entity}
        
        mock_result.__aiter__ = mock_async_iter
        mock_session.run.return_value = mock_result
        
        with patch.object(neo4j_client, 'get_session') as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = mock_session
            mock_get_session.return_value.__aexit__.return_value = None
            
            entities = await neo4j_client.find_entities_by_name("Test", limit=10)
            
            assert len(entities) == 2
            assert all(isinstance(e, GraphEntity) for e in entities)
            assert entities[0].name == "Test Entity 1"
            assert entities[1].name == "Test Entity 2"
    
    @pytest.mark.asyncio
    async def test_query_knowledge(self, neo4j_client: Neo4jClient, mock_session):
        """Test knowledge graph querying."""
        neo4j_client.driver = AsyncMock()
        
        mock_result = AsyncMock()
        mock_data = [
            {
                "e": {"id": "1", "name": "Test Entity", "type": "TEST", "description": "Test description"},
                "relationships": [],
                "related_entities": []
            }
        ]
        
        async def mock_async_iter(self):
            for data in mock_data:
                yield data
        
        mock_result.__aiter__ = mock_async_iter
        mock_session.run.return_value = mock_result
        
        with patch.object(neo4j_client, 'get_session') as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = mock_session
            mock_get_session.return_value.__aexit__.return_value = None
            
            result = await neo4j_client.query_knowledge("test query")
            
            assert isinstance(result, GraphQueryResult)
            assert len(result.entities) == 1
            assert result.entities[0].name == "Test Entity"
    
    @pytest.mark.asyncio
    async def test_execute_cypher(self, neo4j_client: Neo4jClient, mock_session):
        """Test raw Cypher query execution."""
        neo4j_client.driver = AsyncMock()
        
        mock_result = AsyncMock()
        mock_records = [{"count": 5}, {"count": 10}]
        
        async def mock_async_iter(self):
            for record in mock_records:
                yield record
        
        mock_result.__aiter__ = mock_async_iter
        mock_session.run.return_value = mock_result
        
        with patch.object(neo4j_client, 'get_session') as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = mock_session
            mock_get_session.return_value.__aexit__.return_value = None
            
            records = await neo4j_client.execute_cypher("MATCH (n) RETURN count(n) as count")
            
            assert len(records) == 2
            assert records[0]["count"] == 5
            assert records[1]["count"] == 10
    
    @pytest.mark.asyncio
    async def test_get_database_stats(self, neo4j_client: Neo4jClient, mock_session):
        """Test database statistics retrieval."""
        neo4j_client.driver = AsyncMock()
        
        # Mock different query results
        mock_results = {
            "entity_count": {"count": 100},
            "document_count": {"count": 50},
            "concept_count": {"count": 25},
            "relationship_count": {"count": 200},
            "node_labels": {"labels": ["Entity", "Document", "Concept"]},
            "relationship_types": {"types": ["RELATES_TO", "CONTAINS", "PART_OF"]}
        }
        
        def mock_run(query, **kwargs):
            result = AsyncMock()
            # Determine which query is being run and return appropriate result
            for stat_name, mock_data in mock_results.items():
                if stat_name in ["node_labels", "relationship_types"]:
                    if "labels" in query or "relationshipTypes" in query:
                        result.single.return_value = mock_data
                        return result
                else:
                    if "count" in query:
                        result.single.return_value = mock_data
                        return result
            
            # Default return
            result.single.return_value = {"count": 0}
            return result
        
        mock_session.run.side_effect = mock_run
        
        with patch.object(neo4j_client, 'get_session') as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = mock_session
            mock_get_session.return_value.__aexit__.return_value = None
            
            stats = await neo4j_client.get_database_stats()
            
            assert isinstance(stats, dict)
            # At least some stats should be present
            assert len(stats) > 0


class TestGlobalClientFunctions:
    """Test global client management functions."""
    
    @pytest.mark.asyncio
    async def test_get_neo4j_client_creates_instance(self):
        """Test that get_neo4j_client creates a new instance if none exists."""
        # Reset global client
        import oracle.clients.neo4j_client as client_module
        client_module._neo4j_client = None
        
        with patch.object(Neo4jClient, 'connect') as mock_connect, \
             patch.object(Neo4jClient, 'create_schema_constraints') as mock_constraints:
            
            mock_connect.return_value = None
            mock_constraints.return_value = None
            
            client = await get_neo4j_client()
            
            assert isinstance(client, Neo4jClient)
            mock_connect.assert_called_once()
            mock_constraints.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_neo4j_client_returns_existing_instance(self):
        """Test that get_neo4j_client returns existing instance if available."""
        # Set up existing client
        import oracle.clients.neo4j_client as client_module
        existing_client = Neo4jClient()
        client_module._neo4j_client = existing_client
        
        client = await get_neo4j_client()
        
        assert client is existing_client
    
    @pytest.mark.asyncio
    async def test_close_neo4j_client(self):
        """Test closing the global Neo4j client."""
        # Set up existing client
        import oracle.clients.neo4j_client as client_module
        mock_client = AsyncMock(spec=Neo4jClient)
        client_module._neo4j_client = mock_client
        
        await close_neo4j_client()
        
        mock_client.disconnect.assert_called_once()
        assert client_module._neo4j_client is None


class TestDataModels:
    """Test data model classes."""
    
    def test_graph_entity_creation(self):
        """Test GraphEntity model creation."""
        entity = GraphEntity(
            id="test_1",
            name="Test Entity",
            type="TEST",
            description="A test entity",
            properties={"key": "value"}
        )
        
        assert entity.id == "test_1"
        assert entity.name == "Test Entity"
        assert entity.type == "TEST"
        assert entity.description == "A test entity"
        assert entity.properties == {"key": "value"}
    
    def test_graph_relationship_creation(self):
        """Test GraphRelationship model creation."""
        relationship = GraphRelationship(
            id="rel_1",
            type="RELATES_TO",
            source_id="entity_1",
            target_id="entity_2",
            properties={"strength": 0.8}
        )
        
        assert relationship.id == "rel_1"
        assert relationship.type == "RELATES_TO"
        assert relationship.source_id == "entity_1"
        assert relationship.target_id == "entity_2"
        assert relationship.properties == {"strength": 0.8}
    
    def test_graph_query_result_creation(self):
        """Test GraphQueryResult model creation."""
        entity = GraphEntity(id="1", name="Test", type="TEST")
        relationship = GraphRelationship(id="1", type="TEST", source_id="1", target_id="2")
        
        result = GraphQueryResult(
            entities=[entity],
            relationships=[relationship],
            raw_results=[{"test": "data"}],
            query_time=0.5
        )
        
        assert len(result.entities) == 1
        assert len(result.relationships) == 1
        assert len(result.raw_results) == 1
        assert result.query_time == 0.5