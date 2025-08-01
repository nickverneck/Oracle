"""Knowledge retrieval service with hybrid retrieval capabilities."""

import asyncio
from typing import List, Dict, Any, Optional
import structlog

from ..clients.chromadb_client import ChromaDBClient
from ..clients.neo4j_client import Neo4jClient, get_neo4j_client
from ..models.chat import Source
from ..models.errors import OracleException, ErrorCode
from .hybrid_retrieval import HybridKnowledgeRetrieval

logger = structlog.get_logger(__name__)


class KnowledgeRetrievalService:
    """Service for retrieving knowledge from graph and vector databases using hybrid approach."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize knowledge retrieval service.
        
        Args:
            config: Configuration dictionary containing:
                - neo4j: Neo4j connection settings
                - chromadb: ChromaDB connection settings
                - retrieval: Retrieval-specific settings
        """
        self.config = config
        self.neo4j_config = config.get("neo4j", {})
        self.chromadb_config = config.get("chromadb", {})
        self.retrieval_config = config.get("retrieval", {})
        
        # Initialize ChromaDB client
        self.chromadb_client = ChromaDBClient(
            host=self.chromadb_config.get("host", "localhost"),
            port=self.chromadb_config.get("port", 8002),
            embedding_model=self.chromadb_config.get("embedding_model", "all-MiniLM-L6-v2"),
            collection_name=self.chromadb_config.get("collection_name", "oracle_documents")
        )
        
        # Initialize Neo4j client (will be set up lazily)
        self.neo4j_client: Optional[Neo4jClient] = None
        
        # Initialize hybrid retrieval service
        self.hybrid_retrieval: Optional[HybridKnowledgeRetrieval] = None
        
        # Service availability flags
        self._neo4j_available = False
        self._chromadb_available = False
        self._hybrid_initialized = False
        
        logger.info("Initialized knowledge retrieval service")
    
    async def _check_chromadb_availability(self):
        """Check if ChromaDB is available and update status."""
        try:
            health = await self.chromadb_client.health_check()
            self._chromadb_available = health.get("status") == "healthy"
            logger.info("ChromaDB availability check", available=self._chromadb_available)
        except Exception as e:
            self._chromadb_available = False
            logger.warning("ChromaDB availability check failed", error=str(e))
    
    async def _ensure_chromadb_availability(self):
        """Ensure ChromaDB availability is checked before use."""
        if not hasattr(self, '_chromadb_checked'):
            await self._check_chromadb_availability()
            self._chromadb_checked = True
    
    async def _ensure_neo4j_availability(self):
        """Ensure Neo4j availability is checked and client is initialized."""
        if not hasattr(self, '_neo4j_checked'):
            try:
                self.neo4j_client = await get_neo4j_client()
                self._neo4j_available = await self.neo4j_client.health_check()
                logger.info("Neo4j availability check", available=self._neo4j_available)
            except Exception as e:
                self._neo4j_available = False
                logger.warning("Neo4j availability check failed", error=str(e))
            
            self._neo4j_checked = True
    
    async def _ensure_hybrid_retrieval(self):
        """Ensure hybrid retrieval service is initialized."""
        if not self._hybrid_initialized:
            await self._ensure_chromadb_availability()
            await self._ensure_neo4j_availability()
            
            # Initialize hybrid retrieval with available clients
            self.hybrid_retrieval = HybridKnowledgeRetrieval(
                neo4j_client=self.neo4j_client if self._neo4j_available else None,
                chromadb_client=self.chromadb_client if self._chromadb_available else None,
                config=self.retrieval_config
            )
            
            self._hybrid_initialized = True
            logger.info(
                "Initialized hybrid retrieval service",
                neo4j_available=self._neo4j_available,
                chromadb_available=self._chromadb_available
            )
    
    async def retrieve_knowledge(
        self,
        query: str,
        max_sources: int = 5,
        include_graph: bool = True,
        include_vector: bool = True,
        **kwargs
    ) -> List[Source]:
        """Retrieve knowledge from available sources using hybrid approach.
        
        Args:
            query: Search query
            max_sources: Maximum number of sources to return
            include_graph: Whether to include graph database results
            include_vector: Whether to include vector database results
            **kwargs: Additional retrieval options
            
        Returns:
            List of knowledge sources
        """
        # Ensure hybrid retrieval is initialized
        await self._ensure_hybrid_retrieval()
        
        if self.hybrid_retrieval:
            try:
                # Use hybrid retrieval service
                result = await self.hybrid_retrieval.retrieve_knowledge(
                    query=query,
                    max_sources=max_sources,
                    include_graph=include_graph,
                    include_vector=include_vector,
                    **kwargs
                )
                
                logger.info(
                    "Hybrid knowledge retrieval completed",
                    sources_returned=len(result.sources),
                    query_time=result.query_time,
                    cache_hit=result.cache_hit
                )
                
                return result.sources
                
            except Exception as e:
                logger.error("Hybrid retrieval failed, falling back to legacy method", error=str(e))
                # Fall back to legacy retrieval method
                return await self._legacy_retrieve_knowledge(query, max_sources, include_graph, include_vector)
        
        # If hybrid retrieval not available, use legacy method
        return await self._legacy_retrieve_knowledge(query, max_sources, include_graph, include_vector)
    
    async def _legacy_retrieve_knowledge(
        self,
        query: str,
        max_sources: int = 5,
        include_graph: bool = True,
        include_vector: bool = True
    ) -> List[Source]:
        """Legacy knowledge retrieval method (fallback).
        
        Args:
            query: Search query
            max_sources: Maximum number of sources to return
            include_graph: Whether to include graph database results
            include_vector: Whether to include vector database results
            
        Returns:
            List of knowledge sources
        """
        # Ensure availability is checked
        await self._ensure_chromadb_availability()
        await self._ensure_neo4j_availability()
        
        sources = []
        
        # Run graph and vector retrieval concurrently
        tasks = []
        
        if include_graph and self._neo4j_available:
            tasks.append(self._retrieve_from_graph(query, max_sources // 2))
        
        if include_vector and self._chromadb_available:
            tasks.append(self._retrieve_from_vector(query, max_sources // 2))
        
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, Exception):
                    logger.warning("Knowledge retrieval failed", error=str(result))
                elif isinstance(result, list):
                    sources.extend(result)
        
        # If no knowledge sources available, return placeholder sources
        if not sources:
            sources = await self._get_placeholder_sources(query)
        
        # Sort by relevance score and limit results
        sources.sort(key=lambda x: x.relevance_score, reverse=True)
        return sources[:max_sources]
    
    async def _retrieve_from_graph(self, query: str, max_results: int) -> List[Source]:
        """Retrieve knowledge from Neo4j graph database.
        
        Args:
            query: Search query
            max_results: Maximum number of results
            
        Returns:
            List of sources from graph database
        """
        if not self.neo4j_client or not self._neo4j_available:
            logger.debug("Neo4j not available, skipping graph retrieval")
            return []
        
        try:
            # Query the knowledge graph
            graph_result = await self.neo4j_client.query_knowledge(
                query_text=query,
                limit=max_results
            )
            
            sources = []
            query_keywords = set(query.lower().split())
            
            # Convert entities to sources
            for entity in graph_result.entities:
                # Calculate basic relevance score
                relevance_score = self._calculate_entity_relevance(entity, query_keywords)
                
                if relevance_score > 0.1:  # Minimum threshold
                    # Build content from entity
                    content_parts = [f"Entity: {entity.name}"]
                    if entity.description:
                        content_parts.append(f"Description: {entity.description}")
                    
                    content = ". ".join(content_parts)
                    
                    source = Source(
                        type="graph",
                        content=content,
                        relevance_score=relevance_score,
                        metadata={
                            "entity_id": entity.id,
                            "entity_type": entity.type,
                            "entity_name": entity.name,
                            "source_type": "neo4j",
                            "properties": entity.properties
                        }
                    )
                    sources.append(source)
            
            logger.debug(
                "Graph retrieval completed",
                query_length=len(query),
                entities_found=len(graph_result.entities),
                sources_created=len(sources)
            )
            
            return sources
            
        except Exception as e:
            logger.error("Graph retrieval failed", error=str(e))
            return []
    
    def _calculate_entity_relevance(self, entity: Any, query_keywords: set) -> float:
        """Calculate relevance score for a graph entity.
        
        Args:
            entity: Graph entity
            query_keywords: Set of query keywords
            
        Returns:
            Relevance score between 0.0 and 1.0
        """
        score = 0.0
        
        # Check name matching
        if entity.name:
            entity_words = set(entity.name.lower().split())
            name_matches = len(query_keywords.intersection(entity_words))
            if name_matches > 0:
                score += 0.6 * (name_matches / len(query_keywords))
        
        # Check description matching
        if entity.description:
            desc_words = set(entity.description.lower().split())
            desc_matches = len(query_keywords.intersection(desc_words))
            if desc_matches > 0:
                score += 0.4 * (desc_matches / len(query_keywords))
        
        return min(score, 1.0)
    
    async def _retrieve_from_vector(self, query: str, max_results: int) -> List[Source]:
        """Retrieve knowledge from ChromaDB vector database."""
        try:
            # Get similarity threshold from config
            similarity_threshold = self.retrieval_config.get("similarity_threshold", 0.7)
            
            # Perform similarity search
            results = await self.chromadb_client.similarity_search(
                query=query,
                n_results=max_results
            )
            
            sources = []
            for result in results:
                # Filter by similarity threshold
                if result['similarity_score'] >= similarity_threshold:
                    source = Source(
                        type="vector",
                        content=result['document'],
                        relevance_score=result['similarity_score'],
                        metadata={
                            **result['metadata'],
                            "source_type": "chromadb",
                            "document_id": result['id'],
                            "similarity_score": result['similarity_score'],
                            "distance": result['distance']
                        }
                    )
                    sources.append(source)
            
            logger.debug(
                "Retrieved vector knowledge",
                query_length=len(query),
                results_count=len(sources),
                threshold=similarity_threshold
            )
            
            return sources
            
        except Exception as e:
            logger.error("Vector retrieval failed", error=str(e))
            # Return empty list on error to allow graceful degradation
            return []
    
    async def _get_placeholder_sources(self, query: str) -> List[Source]:
        """Get placeholder sources when no knowledge databases are available."""
        return [
            Source(
                type="graph",
                content="Knowledge retrieval services are not yet configured. This is a placeholder response.",
                relevance_score=0.5,
                metadata={
                    "source": "placeholder",
                    "note": "Actual knowledge retrieval will be implemented in tasks 5-7"
                }
            )
        ]
    
    async def health_check(self) -> Dict[str, Any]:
        """Check health of knowledge retrieval services.
        
        Returns:
            Dictionary with health status of each service
        """
        # Ensure services are initialized
        await self._ensure_hybrid_retrieval()
        
        health_status = {
            "neo4j": self._neo4j_available,
            "chromadb": self._chromadb_available,
            "knowledge_service": True,  # Service itself is healthy
            "hybrid_retrieval": self.hybrid_retrieval is not None
        }
        
        # Get hybrid retrieval health if available
        if self.hybrid_retrieval:
            try:
                hybrid_health = await self.hybrid_retrieval.health_check()
                health_status["hybrid_details"] = hybrid_health
            except Exception as e:
                health_status["hybrid_error"] = str(e)
        
        return health_status
    
    async def add_document_to_vector_db(
        self,
        text: str,
        metadata: Dict[str, Any],
        document_id: str,
        chunk_size: int = 1000,
        chunk_overlap: int = 200
    ) -> int:
        """Add a document to the vector database.
        
        Args:
            text: Document text
            metadata: Document metadata
            document_id: Unique document identifier
            chunk_size: Maximum characters per chunk
            chunk_overlap: Overlap between consecutive chunks
            
        Returns:
            Number of chunks created
        """
        # Ensure ChromaDB availability is checked
        await self._ensure_chromadb_availability()
        
        try:
            chunks_created = await self.chromadb_client.add_document_chunks(
                text=text,
                metadata=metadata,
                document_id=document_id,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap
            )
            
            logger.info(
                "Added document to vector database",
                document_id=document_id,
                chunks_created=chunks_created
            )
            
            return chunks_created
            
        except Exception as e:
            logger.error(
                "Failed to add document to vector database",
                document_id=document_id,
                error=str(e)
            )
            raise OracleException(
                message=f"Failed to add document to vector database: {str(e)}",
                error_code=ErrorCode.VECTOR_DB_ERROR
            )
    
    async def get_vector_db_stats(self) -> Dict[str, Any]:
        """Get vector database statistics.
        
        Returns:
            Vector database statistics
        """
        try:
            return await self.chromadb_client.get_collection_stats()
        except Exception as e:
            logger.error("Failed to get vector DB stats", error=str(e))
            return {"error": str(e)}
    
    def get_retrieval_stats(self) -> Dict[str, Any]:
        """Get statistics about knowledge retrieval.
        
        Returns:
            Dictionary with retrieval statistics
        """
        stats = {
            "neo4j_available": self._neo4j_available,
            "chromadb_available": self._chromadb_available,
            "hybrid_initialized": self._hybrid_initialized,
            "config": {
                "max_graph_results": self.retrieval_config.get("max_graph_results", 10),
                "max_vector_results": self.retrieval_config.get("max_vector_results", 10),
                "similarity_threshold": self.retrieval_config.get("similarity_threshold", 0.7)
            }
        }
        
        # Add cache stats if hybrid retrieval is available
        if self.hybrid_retrieval:
            try:
                cache_stats = self.hybrid_retrieval.get_cache_stats()
                stats["cache"] = cache_stats
            except Exception as e:
                stats["cache_error"] = str(e)
        
        return stats
    
    async def clear_knowledge_cache(self) -> int:
        """Clear the knowledge retrieval cache.
        
        Returns:
            Number of cache entries cleared
        """
        if self.hybrid_retrieval:
            return self.hybrid_retrieval.clear_cache()
        return 0