"""Hybrid knowledge retrieval service combining graph and vector databases."""

import asyncio
import hashlib
import time
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict
import structlog

from ..clients.neo4j_client import Neo4jClient, GraphQueryResult
from ..clients.chromadb_client import ChromaDBClient
from ..models.chat import Source
from ..models.errors import OracleException, ErrorCode

logger = structlog.get_logger(__name__)


@dataclass
class RetrievalResult:
    """Container for hybrid retrieval results."""
    sources: List[Source]
    graph_results: Optional[GraphQueryResult] = None
    vector_results: List[Dict[str, Any]] = None
    query_time: float = 0.0
    cache_hit: bool = False


@dataclass
class CacheEntry:
    """Cache entry for storing retrieval results."""
    sources: List[Source]
    timestamp: float
    access_count: int = 0
    
    def is_expired(self, ttl_seconds: int) -> bool:
        """Check if cache entry is expired."""
        return time.time() - self.timestamp > ttl_seconds


class HybridKnowledgeRetrieval:
    """Service for hybrid knowledge retrieval combining graph and vector databases."""
    
    def __init__(
        self,
        neo4j_client: Optional[Neo4jClient] = None,
        chromadb_client: Optional[ChromaDBClient] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """Initialize hybrid knowledge retrieval service.
        
        Args:
            neo4j_client: Neo4j client instance
            chromadb_client: ChromaDB client instance
            config: Configuration dictionary
        """
        self.neo4j_client = neo4j_client
        self.chromadb_client = chromadb_client
        self.config = config or {}
        
        # Retrieval configuration
        self.max_graph_results = self.config.get("max_graph_results", 10)
        self.max_vector_results = self.config.get("max_vector_results", 10)
        self.similarity_threshold = self.config.get("similarity_threshold", 0.7)
        self.graph_weight = self.config.get("graph_weight", 0.6)
        self.vector_weight = self.config.get("vector_weight", 0.4)
        
        # Caching configuration
        self.cache_enabled = self.config.get("cache_enabled", True)
        self.cache_ttl = self.config.get("cache_ttl_seconds", 300)  # 5 minutes
        self.max_cache_size = self.config.get("max_cache_size", 1000)
        
        # In-memory cache for frequently accessed knowledge
        self._cache: Dict[str, CacheEntry] = {}
        
        logger.info(
            "Initialized hybrid knowledge retrieval service",
            cache_enabled=self.cache_enabled,
            cache_ttl=self.cache_ttl,
            max_graph_results=self.max_graph_results,
            max_vector_results=self.max_vector_results
        )
    
    def _generate_cache_key(self, query: str, options: Dict[str, Any]) -> str:
        """Generate cache key for a query and options.
        
        Args:
            query: Search query
            options: Retrieval options
            
        Returns:
            Cache key string
        """
        # Create deterministic hash from query and relevant options
        cache_data = {
            "query": query.lower().strip(),
            "max_sources": options.get("max_sources", 5),
            "include_graph": options.get("include_graph", True),
            "include_vector": options.get("include_vector", True),
            "similarity_threshold": options.get("similarity_threshold", self.similarity_threshold)
        }
        
        cache_string = str(sorted(cache_data.items()))
        return hashlib.md5(cache_string.encode()).hexdigest()
    
    def _get_from_cache(self, cache_key: str) -> Optional[List[Source]]:
        """Get results from cache if available and not expired.
        
        Args:
            cache_key: Cache key to lookup
            
        Returns:
            Cached sources if available, None otherwise
        """
        if not self.cache_enabled or cache_key not in self._cache:
            return None
        
        entry = self._cache[cache_key]
        
        if entry.is_expired(self.cache_ttl):
            # Remove expired entry
            del self._cache[cache_key]
            return None
        
        # Update access count and return cached results
        entry.access_count += 1
        logger.debug("Cache hit", cache_key=cache_key, access_count=entry.access_count)
        return entry.sources
    
    def _store_in_cache(self, cache_key: str, sources: List[Source]) -> None:
        """Store results in cache.
        
        Args:
            cache_key: Cache key
            sources: Sources to cache
        """
        if not self.cache_enabled:
            return
        
        # Implement LRU eviction if cache is full
        if len(self._cache) >= self.max_cache_size:
            # Remove least recently used entries (oldest timestamp)
            sorted_entries = sorted(
                self._cache.items(),
                key=lambda x: x[1].timestamp
            )
            
            # Remove oldest 10% of entries
            entries_to_remove = max(1, len(sorted_entries) // 10)
            for key, _ in sorted_entries[:entries_to_remove]:
                del self._cache[key]
        
        # Store new entry
        self._cache[cache_key] = CacheEntry(
            sources=sources,
            timestamp=time.time()
        )
        
        logger.debug("Stored in cache", cache_key=cache_key, cache_size=len(self._cache))
    
    async def retrieve_knowledge(
        self,
        query: str,
        max_sources: int = 5,
        include_graph: bool = True,
        include_vector: bool = True,
        **kwargs
    ) -> RetrievalResult:
        """Retrieve knowledge using hybrid approach combining graph and vector databases.
        
        Args:
            query: Search query
            max_sources: Maximum number of sources to return
            include_graph: Whether to include graph database results
            include_vector: Whether to include vector database results
            **kwargs: Additional retrieval options
            
        Returns:
            RetrievalResult with combined sources and metadata
        """
        start_time = time.time()
        
        # Generate cache key
        options = {
            "max_sources": max_sources,
            "include_graph": include_graph,
            "include_vector": include_vector,
            "similarity_threshold": kwargs.get("similarity_threshold", self.similarity_threshold),
            **kwargs
        }
        cache_key = self._generate_cache_key(query, options)
        
        # Check cache first
        cached_sources = self._get_from_cache(cache_key)
        if cached_sources:
            return RetrievalResult(
                sources=cached_sources[:max_sources],
                query_time=time.time() - start_time,
                cache_hit=True
            )
        
        # Perform parallel retrieval from both sources
        tasks = []
        graph_results = None
        vector_results = []
        
        if include_graph and self.neo4j_client:
            tasks.append(self._retrieve_from_graph(query, self.max_graph_results))
        
        if include_vector and self.chromadb_client:
            tasks.append(self._retrieve_from_vector(query, self.max_vector_results, **kwargs))
        
        if tasks:
            try:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Process results
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        logger.warning(
                            "Knowledge retrieval failed",
                            source="graph" if i == 0 and include_graph else "vector",
                            error=str(result)
                        )
                    elif include_graph and i == 0:
                        graph_results = result
                    elif include_vector:
                        vector_results = result
                        
            except Exception as e:
                logger.error("Hybrid retrieval failed", error=str(e))
                raise OracleException(
                    message=f"Knowledge retrieval failed: {str(e)}",
                    error_code=ErrorCode.KNOWLEDGE_RETRIEVAL_ERROR
                )
        
        # Merge and rank results
        merged_sources = await self._merge_and_rank_results(
            graph_results=graph_results,
            vector_results=vector_results,
            query=query,
            max_sources=max_sources
        )
        
        # Store in cache
        self._store_in_cache(cache_key, merged_sources)
        
        query_time = time.time() - start_time
        
        logger.info(
            "Completed hybrid knowledge retrieval",
            query_length=len(query),
            sources_returned=len(merged_sources),
            query_time=query_time,
            graph_available=graph_results is not None,
            vector_available=len(vector_results) > 0
        )
        
        return RetrievalResult(
            sources=merged_sources,
            graph_results=graph_results,
            vector_results=vector_results,
            query_time=query_time,
            cache_hit=False
        )
    
    async def _retrieve_from_graph(self, query: str, max_results: int) -> Optional[GraphQueryResult]:
        """Retrieve knowledge from Neo4j graph database.
        
        Args:
            query: Search query
            max_results: Maximum number of results
            
        Returns:
            GraphQueryResult or None if unavailable
        """
        try:
            if not await self.neo4j_client.health_check():
                logger.warning("Neo4j health check failed, skipping graph retrieval")
                return None
            
            # Perform knowledge query
            result = await self.neo4j_client.query_knowledge(
                query_text=query,
                limit=max_results
            )
            
            logger.debug(
                "Graph retrieval completed",
                entities_found=len(result.entities),
                relationships_found=len(result.relationships)
            )
            
            return result
            
        except Exception as e:
            logger.error("Graph retrieval failed", error=str(e))
            return None
    
    async def _retrieve_from_vector(
        self,
        query: str,
        max_results: int,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """Retrieve knowledge from ChromaDB vector database.
        
        Args:
            query: Search query
            max_results: Maximum number of results
            **kwargs: Additional search options
            
        Returns:
            List of vector search results
        """
        try:
            health = await self.chromadb_client.health_check()
            if health.get("status") != "healthy":
                logger.warning("ChromaDB health check failed, skipping vector retrieval")
                return []
            
            # Get similarity threshold
            similarity_threshold = kwargs.get("similarity_threshold", self.similarity_threshold)
            
            # Perform similarity search
            results = await self.chromadb_client.similarity_search(
                query=query,
                n_results=max_results,
                where=kwargs.get("where")
            )
            
            # Filter by similarity threshold
            filtered_results = [
                result for result in results
                if result.get("similarity_score", 0.0) >= similarity_threshold
            ]
            
            logger.debug(
                "Vector retrieval completed",
                total_results=len(results),
                filtered_results=len(filtered_results),
                threshold=similarity_threshold
            )
            
            return filtered_results
            
        except Exception as e:
            logger.error("Vector retrieval failed", error=str(e))
            return []
    
    async def _merge_and_rank_results(
        self,
        graph_results: Optional[GraphQueryResult],
        vector_results: List[Dict[str, Any]],
        query: str,
        max_sources: int
    ) -> List[Source]:
        """Merge and rank results from graph and vector databases.
        
        Args:
            graph_results: Results from graph database
            vector_results: Results from vector database
            query: Original search query
            max_sources: Maximum number of sources to return
            
        Returns:
            List of ranked and merged sources
        """
        sources = []
        
        # Convert graph results to sources
        if graph_results:
            graph_sources = await self._convert_graph_to_sources(graph_results, query)
            sources.extend(graph_sources)
        
        # Convert vector results to sources
        if vector_results:
            vector_sources = self._convert_vector_to_sources(vector_results)
            sources.extend(vector_sources)
        
        # Remove duplicates based on content similarity
        sources = self._deduplicate_sources(sources)
        
        # Rank sources using hybrid scoring
        ranked_sources = self._rank_sources(sources, query)
        
        # Aggregate context for top sources
        final_sources = self._aggregate_context(ranked_sources[:max_sources])
        
        return final_sources
    
    async def _convert_graph_to_sources(
        self,
        graph_results: GraphQueryResult,
        query: str
    ) -> List[Source]:
        """Convert graph query results to Source objects.
        
        Args:
            graph_results: Results from graph database
            query: Original search query
            
        Returns:
            List of Source objects from graph data
        """
        sources = []
        query_keywords = set(query.lower().split())
        
        # Process entities
        for entity in graph_results.entities:
            # Calculate relevance based on name and description matching
            relevance_score = self._calculate_graph_relevance(entity, query_keywords)
            
            if relevance_score > 0.1:  # Minimum relevance threshold
                # Find related entities for context
                related_entities = [
                    rel.target_id if rel.source_id == entity.id else rel.source_id
                    for rel in graph_results.relationships
                    if rel.source_id == entity.id or rel.target_id == entity.id
                ]
                
                # Build content from entity information
                content_parts = [f"Entity: {entity.name}"]
                if entity.description:
                    content_parts.append(f"Description: {entity.description}")
                
                # Add relationship context
                if related_entities:
                    related_names = []
                    for related_id in related_entities[:3]:  # Limit to top 3
                        related_entity = next(
                            (e for e in graph_results.entities if e.id == related_id),
                            None
                        )
                        if related_entity:
                            related_names.append(related_entity.name)
                    
                    if related_names:
                        content_parts.append(f"Related to: {', '.join(related_names)}")
                
                content = ". ".join(content_parts)
                
                source = Source(
                    type="graph",
                    content=content,
                    relevance_score=relevance_score * self.graph_weight,
                    metadata={
                        "entity_id": entity.id,
                        "entity_type": entity.type,
                        "entity_name": entity.name,
                        "related_entities": related_entities[:5],
                        "source_type": "neo4j",
                        "properties": entity.properties
                    }
                )
                sources.append(source)
        
        return sources
    
    def _convert_vector_to_sources(self, vector_results: List[Dict[str, Any]]) -> List[Source]:
        """Convert vector search results to Source objects.
        
        Args:
            vector_results: Results from vector database
            
        Returns:
            List of Source objects from vector data
        """
        sources = []
        
        for result in vector_results:
            # Apply vector weight to similarity score
            weighted_score = result.get("similarity_score", 0.0) * self.vector_weight
            
            source = Source(
                type="vector",
                content=result.get("document", ""),
                relevance_score=weighted_score,
                metadata={
                    **result.get("metadata", {}),
                    "document_id": result.get("id"),
                    "similarity_score": result.get("similarity_score", 0.0),
                    "distance": result.get("distance", 0.0),
                    "source_type": "chromadb"
                }
            )
            sources.append(source)
        
        return sources
    
    def _calculate_graph_relevance(
        self,
        entity: Any,
        query_keywords: set
    ) -> float:
        """Calculate relevance score for a graph entity.
        
        Args:
            entity: Graph entity object
            query_keywords: Set of query keywords
            
        Returns:
            Relevance score between 0.0 and 1.0
        """
        score = 0.0
        
        # Check name matching
        entity_name_words = set(entity.name.lower().split())
        name_matches = len(query_keywords.intersection(entity_name_words))
        if name_matches > 0:
            score += 0.5 * (name_matches / len(query_keywords))
        
        # Check description matching
        if entity.description:
            desc_words = set(entity.description.lower().split())
            desc_matches = len(query_keywords.intersection(desc_words))
            if desc_matches > 0:
                score += 0.3 * (desc_matches / len(query_keywords))
        
        # Check properties matching
        if entity.properties:
            prop_text = " ".join(str(v).lower() for v in entity.properties.values())
            prop_words = set(prop_text.split())
            prop_matches = len(query_keywords.intersection(prop_words))
            if prop_matches > 0:
                score += 0.2 * (prop_matches / len(query_keywords))
        
        return min(score, 1.0)
    
    def _deduplicate_sources(self, sources: List[Source]) -> List[Source]:
        """Remove duplicate sources based on content similarity.
        
        Args:
            sources: List of sources to deduplicate
            
        Returns:
            List of deduplicated sources
        """
        if not sources:
            return sources
        
        deduplicated = []
        seen_content = set()
        
        for source in sources:
            # Create a normalized version of content for comparison
            normalized_content = source.content.lower().strip()
            
            # Simple deduplication based on content hash
            content_hash = hashlib.md5(normalized_content.encode()).hexdigest()
            
            if content_hash not in seen_content:
                seen_content.add(content_hash)
                deduplicated.append(source)
            else:
                # If duplicate found, keep the one with higher relevance score
                existing_idx = next(
                    (i for i, s in enumerate(deduplicated) 
                     if hashlib.md5(s.content.lower().strip().encode()).hexdigest() == content_hash),
                    None
                )
                
                if existing_idx is not None and source.relevance_score > deduplicated[existing_idx].relevance_score:
                    deduplicated[existing_idx] = source
        
        logger.debug(
            "Deduplicated sources",
            original_count=len(sources),
            deduplicated_count=len(deduplicated)
        )
        
        return deduplicated
    
    def _rank_sources(self, sources: List[Source], query: str) -> List[Source]:
        """Rank sources using hybrid scoring algorithm.
        
        Args:
            sources: List of sources to rank
            query: Original search query
            
        Returns:
            List of sources sorted by relevance score
        """
        query_keywords = set(query.lower().split())
        
        for source in sources:
            # Base score from retrieval
            base_score = source.relevance_score
            
            # Boost score based on content quality indicators
            content_boost = self._calculate_content_boost(source.content, query_keywords)
            
            # Boost score based on source type preferences
            type_boost = self._calculate_type_boost(source.type)
            
            # Boost score based on metadata quality
            metadata_boost = self._calculate_metadata_boost(source.metadata)
            
            # Calculate final score
            final_score = base_score + content_boost + type_boost + metadata_boost
            source.relevance_score = min(final_score, 1.0)
        
        # Sort by relevance score (descending)
        ranked_sources = sorted(sources, key=lambda x: x.relevance_score, reverse=True)
        
        logger.debug(
            "Ranked sources",
            total_sources=len(sources),
            top_score=ranked_sources[0].relevance_score if ranked_sources else 0.0
        )
        
        return ranked_sources
    
    def _calculate_content_boost(self, content: str, query_keywords: set) -> float:
        """Calculate content quality boost for ranking.
        
        Args:
            content: Source content
            query_keywords: Set of query keywords
            
        Returns:
            Boost score between 0.0 and 0.2
        """
        boost = 0.0
        content_words = set(content.lower().split())
        
        # Boost for keyword density
        keyword_matches = len(query_keywords.intersection(content_words))
        if keyword_matches > 0:
            boost += 0.1 * (keyword_matches / len(query_keywords))
        
        # Boost for content length (prefer moderate length)
        content_length = len(content)
        if 100 <= content_length <= 500:
            boost += 0.05
        elif 50 <= content_length <= 1000:
            boost += 0.02
        
        return min(boost, 0.2)
    
    def _calculate_type_boost(self, source_type: str) -> float:
        """Calculate source type boost for ranking.
        
        Args:
            source_type: Type of source (graph or vector)
            
        Returns:
            Boost score between 0.0 and 0.1
        """
        # Slight preference for graph sources as they contain structured knowledge
        if source_type == "graph":
            return 0.05
        elif source_type == "vector":
            return 0.03
        return 0.0
    
    def _calculate_metadata_boost(self, metadata: Dict[str, Any]) -> float:
        """Calculate metadata quality boost for ranking.
        
        Args:
            metadata: Source metadata
            
        Returns:
            Boost score between 0.0 and 0.1
        """
        boost = 0.0
        
        # Boost for rich metadata
        if len(metadata) > 3:
            boost += 0.02
        
        # Boost for specific metadata indicators
        if metadata.get("entity_type") or metadata.get("document_type"):
            boost += 0.02
        
        if metadata.get("related_entities") or metadata.get("parent_document_id"):
            boost += 0.02
        
        # Boost for high-quality sources
        if metadata.get("source_type") in ["neo4j", "chromadb"]:
            boost += 0.02
        
        return min(boost, 0.1)
    
    def _aggregate_context(self, sources: List[Source]) -> List[Source]:
        """Aggregate context information for sources.
        
        Args:
            sources: List of sources to aggregate context for
            
        Returns:
            List of sources with aggregated context
        """
        # Group sources by type for context aggregation
        graph_sources = [s for s in sources if s.type == "graph"]
        vector_sources = [s for s in sources if s.type == "vector"]
        
        # Add cross-references between related sources
        for graph_source in graph_sources:
            related_entities = graph_source.metadata.get("related_entities", [])
            
            # Find vector sources that might be related
            related_vector_sources = []
            for vector_source in vector_sources:
                vector_content = vector_source.content.lower()
                entity_name = graph_source.metadata.get("entity_name", "").lower()
                
                if entity_name and entity_name in vector_content:
                    related_vector_sources.append(vector_source.metadata.get("document_id"))
            
            if related_vector_sources:
                graph_source.metadata["related_documents"] = related_vector_sources[:3]
        
        # Add source attribution
        for source in sources:
            source.metadata["retrieval_timestamp"] = time.time()
            source.metadata["retrieval_method"] = "hybrid"
        
        return sources
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        if not self.cache_enabled:
            return {"cache_enabled": False}
        
        total_access_count = sum(entry.access_count for entry in self._cache.values())
        
        return {
            "cache_enabled": True,
            "cache_size": len(self._cache),
            "max_cache_size": self.max_cache_size,
            "cache_ttl": self.cache_ttl,
            "total_access_count": total_access_count,
            "average_access_count": total_access_count / len(self._cache) if self._cache else 0
        }
    
    def clear_cache(self) -> int:
        """Clear the knowledge cache.
        
        Returns:
            Number of entries cleared
        """
        cleared_count = len(self._cache)
        self._cache.clear()
        logger.info("Cleared knowledge cache", entries_cleared=cleared_count)
        return cleared_count
    
    async def health_check(self) -> Dict[str, Any]:
        """Check health of hybrid retrieval service.
        
        Returns:
            Health status information
        """
        health_status = {
            "service": "healthy",
            "cache_enabled": self.cache_enabled,
            "cache_size": len(self._cache) if self.cache_enabled else 0
        }
        
        # Check Neo4j health
        if self.neo4j_client:
            try:
                neo4j_healthy = await self.neo4j_client.health_check()
                health_status["neo4j"] = "healthy" if neo4j_healthy else "unhealthy"
            except Exception as e:
                health_status["neo4j"] = f"error: {str(e)}"
        else:
            health_status["neo4j"] = "not_configured"
        
        # Check ChromaDB health
        if self.chromadb_client:
            try:
                chromadb_health = await self.chromadb_client.health_check()
                health_status["chromadb"] = chromadb_health.get("status", "unknown")
            except Exception as e:
                health_status["chromadb"] = f"error: {str(e)}"
        else:
            health_status["chromadb"] = "not_configured"
        
        return health_status