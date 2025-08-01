"""Knowledge graph builder service that combines entity extraction with Neo4j storage."""

import logging
from typing import List, Dict, Any, Optional, Tuple
import uuid

from oracle.clients.neo4j_client import Neo4jClient, GraphEntity, GraphRelationship
from oracle.services.entity_extraction import (
    EntityExtractor,
    ExtractedEntity,
    ExtractedRelationship
)

logger = logging.getLogger(__name__)


class KnowledgeGraphBuilder:
    """Service for building knowledge graphs from text using entity extraction and Neo4j."""
    
    def __init__(self, neo4j_client: Neo4jClient):
        """Initialize the knowledge graph builder.
        
        Args:
            neo4j_client: Neo4j client instance for graph operations
        """
        self.neo4j_client = neo4j_client
        self.entity_extractor = EntityExtractor()
        self._entity_cache: Dict[str, str] = {}  # Maps entity names to IDs
    
    async def process_document(
        self,
        document_id: str,
        title: str,
        content: str,
        min_entity_confidence: float = 0.5,
        min_relationship_confidence: float = 0.4
    ) -> Dict[str, Any]:
        """Process a document and add its entities and relationships to the knowledge graph.
        
        Args:
            document_id: Unique identifier for the document
            title: Document title
            content: Document content to process
            min_entity_confidence: Minimum confidence threshold for entities
            min_relationship_confidence: Minimum confidence threshold for relationships
            
        Returns:
            Dictionary with processing results and statistics
        """
        logger.info(f"Processing document {document_id}: {title}")
        
        try:
            # Extract entities and relationships from content
            entities = self.entity_extractor.extract_entities(
                content, min_confidence=min_entity_confidence
            )
            relationships = self.entity_extractor.extract_relationships(
                content, entities, min_confidence=min_relationship_confidence
            )
            
            logger.info(f"Extracted {len(entities)} entities and {len(relationships)} relationships")
            
            # Create document node
            document_entity = await self._create_document_entity(document_id, title, content)
            
            # Process entities
            created_entities = []
            for entity in entities:
                graph_entity = await self._process_entity(entity, document_id)
                if graph_entity:
                    created_entities.append(graph_entity)
            
            # Process relationships
            created_relationships = []
            for relationship in relationships:
                graph_relationship = await self._process_relationship(relationship)
                if graph_relationship:
                    created_relationships.append(graph_relationship)
            
            # Create relationships between document and entities
            document_entity_relationships = []
            for entity in created_entities:
                try:
                    doc_rel = await self.neo4j_client.create_relationship(
                        source_id=document_entity.id,
                        target_id=entity.id,
                        relationship_type="CONTAINS",
                        properties={
                            "extraction_confidence": next(
                                (e.confidence for e in entities if e.name == entity.name), 0.5
                            )
                        }
                    )
                    document_entity_relationships.append(doc_rel)
                except Exception as e:
                    logger.warning(f"Failed to create document-entity relationship: {e}")
            
            return {
                "document_id": document_id,
                "document_entity_id": document_entity.id,
                "entities_created": len(created_entities),
                "relationships_created": len(created_relationships),
                "document_relationships_created": len(document_entity_relationships),
                "total_entities_extracted": len(entities),
                "total_relationships_extracted": len(relationships),
                "processing_status": "success"
            }
            
        except Exception as e:
            logger.error(f"Failed to process document {document_id}: {e}")
            return {
                "document_id": document_id,
                "processing_status": "error",
                "error_message": str(e)
            }
    
    async def _create_document_entity(
        self,
        document_id: str,
        title: str,
        content: str
    ) -> GraphEntity:
        """Create a document entity in the knowledge graph.
        
        Args:
            document_id: Document identifier
            title: Document title
            content: Document content
            
        Returns:
            Created GraphEntity for the document
        """
        entity_id = f"doc_{document_id}"
        
        return await self.neo4j_client.create_entity(
            entity_id=entity_id,
            name=title,
            entity_type="DOCUMENT",
            description=f"Document: {title}",
            properties={
                "document_id": document_id,
                "content_length": len(content),
                "content_preview": content[:200] + "..." if len(content) > 200 else content
            }
        )
    
    async def _process_entity(
        self,
        extracted_entity: ExtractedEntity,
        document_id: str
    ) -> Optional[GraphEntity]:
        """Process an extracted entity and add it to the knowledge graph.
        
        Args:
            extracted_entity: Entity extracted from text
            document_id: ID of the source document
            
        Returns:
            Created or existing GraphEntity, or None if processing failed
        """
        try:
            # Generate a consistent entity ID
            entity_key = f"{extracted_entity.entity_type}_{extracted_entity.name.lower().replace(' ', '_')}"
            
            # Check if entity already exists in cache
            if entity_key in self._entity_cache:
                entity_id = self._entity_cache[entity_key]
                # Try to find existing entity
                existing_entities = await self.neo4j_client.find_entities_by_name(
                    extracted_entity.name, limit=1
                )
                if existing_entities:
                    return existing_entities[0]
            
            # Create new entity
            entity_id = f"entity_{uuid.uuid4().hex[:8]}"
            self._entity_cache[entity_key] = entity_id
            
            graph_entity = await self.neo4j_client.create_entity(
                entity_id=entity_id,
                name=extracted_entity.name,
                entity_type=extracted_entity.entity_type,
                description=f"Extracted from document {document_id}",
                properties={
                    "extraction_confidence": extracted_entity.confidence,
                    "extraction_context": extracted_entity.context,
                    "source_document": document_id,
                    **extracted_entity.properties
                }
            )
            
            logger.debug(f"Created entity: {graph_entity.name} ({graph_entity.type})")
            return graph_entity
            
        except Exception as e:
            logger.error(f"Failed to process entity {extracted_entity.name}: {e}")
            return None
    
    async def _process_relationship(
        self,
        extracted_relationship: ExtractedRelationship
    ) -> Optional[GraphRelationship]:
        """Process an extracted relationship and add it to the knowledge graph.
        
        Args:
            extracted_relationship: Relationship extracted from text
            
        Returns:
            Created GraphRelationship, or None if processing failed
        """
        try:
            # Find source and target entities
            source_entities = await self.neo4j_client.find_entities_by_name(
                extracted_relationship.source_entity, limit=1
            )
            target_entities = await self.neo4j_client.find_entities_by_name(
                extracted_relationship.target_entity, limit=1
            )
            
            if not source_entities or not target_entities:
                logger.debug(f"Could not find entities for relationship: {extracted_relationship.source_entity} -> {extracted_relationship.target_entity}")
                return None
            
            source_entity = source_entities[0]
            target_entity = target_entities[0]
            
            # Create relationship
            graph_relationship = await self.neo4j_client.create_relationship(
                source_id=source_entity.id,
                target_id=target_entity.id,
                relationship_type=extracted_relationship.relationship_type,
                properties={
                    "extraction_confidence": extracted_relationship.confidence,
                    "extraction_context": extracted_relationship.context,
                    **extracted_relationship.properties
                }
            )
            
            logger.debug(f"Created relationship: {source_entity.name} -{extracted_relationship.relationship_type}-> {target_entity.name}")
            return graph_relationship
            
        except Exception as e:
            logger.error(f"Failed to process relationship {extracted_relationship.source_entity} -> {extracted_relationship.target_entity}: {e}")
            return None
    
    async def query_related_knowledge(
        self,
        query_text: str,
        max_entities: int = 10,
        max_depth: int = 2
    ) -> Dict[str, Any]:
        """Query the knowledge graph for information related to the query text.
        
        Args:
            query_text: Natural language query
            max_entities: Maximum number of entities to return
            max_depth: Maximum traversal depth for relationships
            
        Returns:
            Dictionary with query results and related knowledge
        """
        try:
            # Query the knowledge graph
            query_result = await self.neo4j_client.query_knowledge(
                query_text, limit=max_entities
            )
            
            # For each found entity, get related entities
            related_knowledge = {}
            for entity in query_result.entities[:5]:  # Limit to top 5 entities
                related_result = await self.neo4j_client.find_related_entities(
                    entity.id, max_depth=max_depth, limit=10
                )
                related_knowledge[entity.name] = {
                    "entity": entity,
                    "related_entities": related_result.entities,
                    "relationships": related_result.relationships
                }
            
            return {
                "query": query_text,
                "direct_matches": query_result.entities,
                "direct_relationships": query_result.relationships,
                "related_knowledge": related_knowledge,
                "total_entities_found": len(query_result.entities),
                "total_relationships_found": len(query_result.relationships)
            }
            
        except Exception as e:
            logger.error(f"Failed to query related knowledge for '{query_text}': {e}")
            return {
                "query": query_text,
                "error": str(e),
                "direct_matches": [],
                "direct_relationships": [],
                "related_knowledge": {}
            }
    
    async def get_knowledge_stats(self) -> Dict[str, Any]:
        """Get statistics about the knowledge graph.
        
        Returns:
            Dictionary with knowledge graph statistics
        """
        try:
            stats = await self.neo4j_client.get_database_stats()
            return {
                "knowledge_graph_stats": stats,
                "entity_cache_size": len(self._entity_cache)
            }
        except Exception as e:
            logger.error(f"Failed to get knowledge stats: {e}")
            return {"error": str(e)}
    
    def clear_entity_cache(self) -> None:
        """Clear the entity cache."""
        self._entity_cache.clear()
        logger.info("Entity cache cleared")