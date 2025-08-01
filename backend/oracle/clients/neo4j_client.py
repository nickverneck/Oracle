"""Neo4j graph database client for knowledge graph operations."""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Tuple
from contextlib import asynccontextmanager

from neo4j import AsyncGraphDatabase, AsyncDriver, AsyncSession
from neo4j.exceptions import ServiceUnavailable, AuthError, Neo4jError
from pydantic import BaseModel

from oracle.core.config import get_settings

logger = logging.getLogger(__name__)


class GraphEntity(BaseModel):
    """Represents an entity in the knowledge graph."""
    
    id: str
    name: str
    type: str
    description: Optional[str] = None
    properties: Dict[str, Any] = {}


class GraphRelationship(BaseModel):
    """Represents a relationship in the knowledge graph."""
    
    id: str
    type: str
    source_id: str
    target_id: str
    properties: Dict[str, Any] = {}


class GraphQueryResult(BaseModel):
    """Result from a graph query operation."""
    
    entities: List[GraphEntity] = []
    relationships: List[GraphRelationship] = []
    raw_results: List[Dict[str, Any]] = []
    query_time: Optional[float] = None


class Neo4jClientError(Exception):
    """Exception raised by Neo4j client operations."""
    pass


class Neo4jClient:
    """Neo4j graph database client with connection pooling and async support."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize Neo4j client with configuration.
        
        Args:
            config: Optional configuration dict, uses settings if not provided
        """
        settings = get_settings()
        self.config = config or {
            "uri": settings.NEO4J_URI,
            "username": settings.NEO4J_USERNAME,
            "password": settings.NEO4J_PASSWORD,
        }
        
        self.driver: Optional[AsyncDriver] = None
        self._connection_pool_size = 10
        self._connection_timeout = 30
        
    async def connect(self) -> None:
        """Establish connection to Neo4j database."""
        try:
            self.driver = AsyncGraphDatabase.driver(
                self.config["uri"],
                auth=(self.config["username"], self.config["password"]),
                max_connection_pool_size=self._connection_pool_size,
                connection_timeout=self._connection_timeout,
            )
            
            # Verify connectivity
            await self.driver.verify_connectivity()
            logger.info("Successfully connected to Neo4j database")
            
        except AuthError as e:
            logger.error(f"Neo4j authentication failed: {e}")
            raise Neo4jClientError(f"Authentication failed: {e}")
        except ServiceUnavailable as e:
            logger.error(f"Neo4j service unavailable: {e}")
            raise Neo4jClientError(f"Service unavailable: {e}")
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            raise Neo4jClientError(f"Connection failed: {e}")
    
    async def disconnect(self) -> None:
        """Close connection to Neo4j database."""
        if self.driver:
            await self.driver.close()
            self.driver = None
            logger.info("Disconnected from Neo4j database")
    
    @asynccontextmanager
    async def get_session(self):
        """Get an async session with automatic cleanup."""
        if not self.driver:
            raise Neo4jClientError("Not connected to Neo4j database")
        
        session = self.driver.session()
        try:
            yield session
        finally:
            await session.close()
    
    async def health_check(self) -> bool:
        """Check if Neo4j service is healthy and accessible.
        
        Returns:
            True if service is healthy, False otherwise
        """
        try:
            if not self.driver:
                await self.connect()
            
            async with self.get_session() as session:
                result = await session.run("RETURN 1 as health")
                record = await result.single()
                return record and record["health"] == 1
                
        except Exception as e:
            logger.error(f"Neo4j health check failed: {e}")
            return False
    
    async def create_schema_constraints(self) -> None:
        """Create database schema constraints for entities and relationships."""
        constraints = [
            # Entity constraints
            "CREATE CONSTRAINT entity_id_unique IF NOT EXISTS FOR (e:Entity) REQUIRE e.id IS UNIQUE",
            "CREATE CONSTRAINT document_id_unique IF NOT EXISTS FOR (d:Document) REQUIRE d.id IS UNIQUE",
            "CREATE CONSTRAINT concept_name_unique IF NOT EXISTS FOR (c:Concept) REQUIRE c.name IS UNIQUE",
            
            # Indexes for performance
            "CREATE INDEX entity_name_index IF NOT EXISTS FOR (e:Entity) ON (e.name)",
            "CREATE INDEX entity_type_index IF NOT EXISTS FOR (e:Entity) ON (e.type)",
            "CREATE INDEX document_title_index IF NOT EXISTS FOR (d:Document) ON (d.title)",
            "CREATE INDEX concept_category_index IF NOT EXISTS FOR (c:Concept) ON (c.category)",
        ]
        
        try:
            async with self.get_session() as session:
                for constraint in constraints:
                    try:
                        await session.run(constraint)
                        logger.debug(f"Applied constraint: {constraint}")
                    except Neo4jError as e:
                        # Constraint might already exist, log but continue
                        logger.debug(f"Constraint application result: {e}")
                        
            logger.info("Schema constraints and indexes created successfully")
            
        except Exception as e:
            logger.error(f"Failed to create schema constraints: {e}")
            raise Neo4jClientError(f"Schema creation failed: {e}")
    
    async def create_entity(
        self,
        entity_id: str,
        name: str,
        entity_type: str,
        description: Optional[str] = None,
        properties: Optional[Dict[str, Any]] = None
    ) -> GraphEntity:
        """Create a new entity in the knowledge graph.
        
        Args:
            entity_id: Unique identifier for the entity
            name: Human-readable name of the entity
            entity_type: Type/category of the entity
            description: Optional description of the entity
            properties: Additional properties as key-value pairs
            
        Returns:
            Created GraphEntity
        """
        props = properties or {}
        props.update({
            "id": entity_id,
            "name": name,
            "type": entity_type,
            "description": description,
            "created_at": "datetime()"
        })
        
        # Build property string for Cypher query
        prop_string = ", ".join([f"{k}: ${k}" for k in props.keys() if props[k] is not None])
        
        query = f"""
        CREATE (e:Entity {{{prop_string}}})
        RETURN e
        """
        
        try:
            async with self.get_session() as session:
                result = await session.run(query, **{k: v for k, v in props.items() if v is not None})
                record = await result.single()
                
                if record:
                    node = record["e"]
                    return GraphEntity(
                        id=node["id"],
                        name=node["name"],
                        type=node["type"],
                        description=node.get("description"),
                        properties=dict(node)
                    )
                else:
                    raise Neo4jClientError("Failed to create entity")
                    
        except Exception as e:
            logger.error(f"Failed to create entity {entity_id}: {e}")
            raise Neo4jClientError(f"Entity creation failed: {e}")
    
    async def create_relationship(
        self,
        source_id: str,
        target_id: str,
        relationship_type: str,
        properties: Optional[Dict[str, Any]] = None
    ) -> GraphRelationship:
        """Create a relationship between two entities.
        
        Args:
            source_id: ID of the source entity
            target_id: ID of the target entity
            relationship_type: Type of relationship
            properties: Additional relationship properties
            
        Returns:
            Created GraphRelationship
        """
        props = properties or {}
        props["created_at"] = "datetime()"
        
        prop_string = ", ".join([f"{k}: ${k}" for k in props.keys()])
        
        query = f"""
        MATCH (source:Entity {{id: $source_id}})
        MATCH (target:Entity {{id: $target_id}})
        CREATE (source)-[r:{relationship_type} {{{prop_string}}}]->(target)
        RETURN r, id(r) as rel_id
        """
        
        try:
            async with self.get_session() as session:
                result = await session.run(
                    query,
                    source_id=source_id,
                    target_id=target_id,
                    **props
                )
                record = await result.single()
                
                if record:
                    rel = record["r"]
                    rel_id = str(record["rel_id"])
                    
                    return GraphRelationship(
                        id=rel_id,
                        type=relationship_type,
                        source_id=source_id,
                        target_id=target_id,
                        properties=dict(rel)
                    )
                else:
                    raise Neo4jClientError("Failed to create relationship")
                    
        except Exception as e:
            logger.error(f"Failed to create relationship {source_id} -> {target_id}: {e}")
            raise Neo4jClientError(f"Relationship creation failed: {e}")    

    async def find_entities_by_name(self, name: str, limit: int = 10) -> List[GraphEntity]:
        """Find entities by name using fuzzy matching.
        
        Args:
            name: Name to search for
            limit: Maximum number of results to return
            
        Returns:
            List of matching GraphEntity objects
        """
        query = """
        MATCH (e:Entity)
        WHERE toLower(e.name) CONTAINS toLower($name)
        RETURN e
        ORDER BY e.name
        LIMIT $limit
        """
        
        try:
            async with self.get_session() as session:
                result = await session.run(query, name=name, limit=limit)
                entities = []
                
                async for record in result:
                    node = record["e"]
                    entities.append(GraphEntity(
                        id=node["id"],
                        name=node["name"],
                        type=node["type"],
                        description=node.get("description"),
                        properties=dict(node)
                    ))
                
                return entities
                
        except Exception as e:
            logger.error(f"Failed to find entities by name '{name}': {e}")
            raise Neo4jClientError(f"Entity search failed: {e}")
    
    async def find_related_entities(
        self,
        entity_id: str,
        relationship_types: Optional[List[str]] = None,
        max_depth: int = 2,
        limit: int = 20
    ) -> GraphQueryResult:
        """Find entities related to a given entity.
        
        Args:
            entity_id: ID of the source entity
            relationship_types: Optional list of relationship types to filter by
            max_depth: Maximum traversal depth
            limit: Maximum number of results
            
        Returns:
            GraphQueryResult with related entities and relationships
        """
        rel_filter = ""
        if relationship_types:
            rel_types = "|".join(relationship_types)
            rel_filter = f":{rel_types}"
        
        query = f"""
        MATCH path = (source:Entity {{id: $entity_id}})-[r{rel_filter}*1..{max_depth}]-(related:Entity)
        WITH source, related, relationships(path) as rels
        RETURN DISTINCT source, related, rels
        LIMIT $limit
        """
        
        try:
            async with self.get_session() as session:
                result = await session.run(
                    query,
                    entity_id=entity_id,
                    limit=limit
                )
                
                entities = []
                relationships = []
                raw_results = []
                
                async for record in result:
                    raw_results.append(dict(record))
                    
                    # Process source entity
                    source_node = record["source"]
                    source_entity = GraphEntity(
                        id=source_node["id"],
                        name=source_node["name"],
                        type=source_node["type"],
                        description=source_node.get("description"),
                        properties=dict(source_node)
                    )
                    if source_entity not in entities:
                        entities.append(source_entity)
                    
                    # Process related entity
                    related_node = record["related"]
                    related_entity = GraphEntity(
                        id=related_node["id"],
                        name=related_node["name"],
                        type=related_node["type"],
                        description=related_node.get("description"),
                        properties=dict(related_node)
                    )
                    if related_entity not in entities:
                        entities.append(related_entity)
                    
                    # Process relationships
                    for rel in record["rels"]:
                        relationship = GraphRelationship(
                            id=str(rel.id),
                            type=rel.type,
                            source_id=rel.start_node["id"],
                            target_id=rel.end_node["id"],
                            properties=dict(rel)
                        )
                        if relationship not in relationships:
                            relationships.append(relationship)
                
                return GraphQueryResult(
                    entities=entities,
                    relationships=relationships,
                    raw_results=raw_results
                )
                
        except Exception as e:
            logger.error(f"Failed to find related entities for '{entity_id}': {e}")
            raise Neo4jClientError(f"Related entity search failed: {e}")
    
    async def query_knowledge(
        self,
        query_text: str,
        entity_types: Optional[List[str]] = None,
        limit: int = 10
    ) -> GraphQueryResult:
        """Query the knowledge graph for relevant information.
        
        Args:
            query_text: Natural language query text
            entity_types: Optional list of entity types to filter by
            limit: Maximum number of results
            
        Returns:
            GraphQueryResult with relevant entities and relationships
        """
        # Simple keyword-based search - can be enhanced with NLP
        keywords = query_text.lower().split()
        
        type_filter = ""
        if entity_types:
            type_list = "', '".join(entity_types)
            type_filter = f"AND e.type IN ['{type_list}']"
        
        query = f"""
        MATCH (e:Entity)
        WHERE ANY(keyword IN $keywords WHERE 
            toLower(e.name) CONTAINS keyword OR 
            toLower(e.description) CONTAINS keyword
        ) {type_filter}
        OPTIONAL MATCH (e)-[r]-(related:Entity)
        RETURN e, collect(DISTINCT r) as relationships, collect(DISTINCT related) as related_entities
        ORDER BY e.name
        LIMIT $limit
        """
        
        try:
            async with self.get_session() as session:
                result = await session.run(
                    query,
                    keywords=keywords,
                    limit=limit
                )
                
                entities = []
                relationships = []
                raw_results = []
                
                async for record in result:
                    raw_results.append(dict(record))
                    
                    # Process main entity
                    entity_node = record["e"]
                    entity = GraphEntity(
                        id=entity_node["id"],
                        name=entity_node["name"],
                        type=entity_node["type"],
                        description=entity_node.get("description"),
                        properties=dict(entity_node)
                    )
                    entities.append(entity)
                    
                    # Process relationships
                    for rel in record["relationships"]:
                        if rel:  # Skip None values
                            relationship = GraphRelationship(
                                id=str(rel.id),
                                type=rel.type,
                                source_id=rel.start_node["id"],
                                target_id=rel.end_node["id"],
                                properties=dict(rel)
                            )
                            relationships.append(relationship)
                    
                    # Process related entities
                    for related_node in record["related_entities"]:
                        if related_node:  # Skip None values
                            related_entity = GraphEntity(
                                id=related_node["id"],
                                name=related_node["name"],
                                type=related_node["type"],
                                description=related_node.get("description"),
                                properties=dict(related_node)
                            )
                            if related_entity not in entities:
                                entities.append(related_entity)
                
                return GraphQueryResult(
                    entities=entities,
                    relationships=relationships,
                    raw_results=raw_results
                )
                
        except Exception as e:
            logger.error(f"Failed to query knowledge graph: {e}")
            raise Neo4jClientError(f"Knowledge query failed: {e}")
    
    async def execute_cypher(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Execute a raw Cypher query.
        
        Args:
            query: Cypher query string
            parameters: Optional query parameters
            
        Returns:
            List of result records as dictionaries
        """
        try:
            async with self.get_session() as session:
                result = await session.run(query, **(parameters or {}))
                records = []
                
                async for record in result:
                    records.append(dict(record))
                
                return records
                
        except Exception as e:
            logger.error(f"Failed to execute Cypher query: {e}")
            raise Neo4jClientError(f"Cypher execution failed: {e}")
    
    async def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics and health information.
        
        Returns:
            Dictionary with database statistics
        """
        queries = {
            "entity_count": "MATCH (e:Entity) RETURN count(e) as count",
            "document_count": "MATCH (d:Document) RETURN count(d) as count",
            "concept_count": "MATCH (c:Concept) RETURN count(c) as count",
            "relationship_count": "MATCH ()-[r]->() RETURN count(r) as count",
            "node_labels": "CALL db.labels() YIELD label RETURN collect(label) as labels",
            "relationship_types": "CALL db.relationshipTypes() YIELD relationshipType RETURN collect(relationshipType) as types"
        }
        
        stats = {}
        
        try:
            async with self.get_session() as session:
                for stat_name, query in queries.items():
                    result = await session.run(query)
                    record = await result.single()
                    
                    if stat_name in ["node_labels", "relationship_types"]:
                        stats[stat_name] = record[list(record.keys())[0]]
                    else:
                        stats[stat_name] = record["count"]
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get database stats: {e}")
            return {"error": str(e)}


# Global client instance
_neo4j_client: Optional[Neo4jClient] = None


async def get_neo4j_client() -> Neo4jClient:
    """Get or create the global Neo4j client instance.
    
    Returns:
        Neo4jClient instance
    """
    global _neo4j_client
    
    if _neo4j_client is None:
        _neo4j_client = Neo4jClient()
        await _neo4j_client.connect()
        await _neo4j_client.create_schema_constraints()
    
    return _neo4j_client


async def close_neo4j_client() -> None:
    """Close the global Neo4j client connection."""
    global _neo4j_client
    
    if _neo4j_client:
        await _neo4j_client.disconnect()
        _neo4j_client = None