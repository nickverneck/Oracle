"""ChromaDB client for vector database operations."""

import asyncio
import hashlib
import structlog
from typing import Any, Dict, List, Optional, Tuple

import chromadb
from chromadb.config import Settings as ChromaSettings
from chromadb.utils import embedding_functions
from sentence_transformers import SentenceTransformer

from oracle.models.errors import OracleException, ErrorCode

logger = structlog.get_logger(__name__)


class ChromaDBClient:
    """Client for ChromaDB vector database operations."""
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 8002,
        embedding_model: str = "all-MiniLM-L6-v2",
        collection_name: str = "oracle_documents"
    ):
        """Initialize ChromaDB client.
        
        Args:
            host: ChromaDB server host
            port: ChromaDB server port
            embedding_model: Sentence transformer model for embeddings
            collection_name: Default collection name
        """
        self.host = host
        self.port = port
        self.embedding_model_name = embedding_model
        self.collection_name = collection_name
        
        # Initialize ChromaDB client
        self.client = chromadb.HttpClient(
            host=host,
            port=port,
            settings=ChromaSettings(
                anonymized_telemetry=False
            )
        )
        
        # Initialize embedding function
        self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=embedding_model
        )
        
        # Cache for sentence transformer model (for chunking operations)
        self._sentence_transformer: Optional[SentenceTransformer] = None
        
        logger.info(
            "Initialized ChromaDB client",
            host=host,
            port=port,
            embedding_model=embedding_model
        )
    
    async def health_check(self) -> Dict[str, Any]:
        """Check ChromaDB service health.
        
        Returns:
            Health status information
        """
        try:
            # Run in thread pool since chromadb client is synchronous
            loop = asyncio.get_event_loop()
            heartbeat = await loop.run_in_executor(None, self.client.heartbeat)
            
            collections = await loop.run_in_executor(None, self.client.list_collections)
            
            return {
                "status": "healthy",
                "heartbeat": heartbeat,
                "collections_count": len(collections),
                "embedding_model": self.embedding_model_name
            }
        except Exception as e:
            logger.error("ChromaDB health check failed", error=str(e))
            return {
                "status": "unhealthy",
                "error": str(e),
                "embedding_model": self.embedding_model_name
            }
    
    async def create_collection(
        self,
        name: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Create a new collection.
        
        Args:
            name: Collection name
            metadata: Optional collection metadata
            
        Returns:
            True if collection was created successfully
        """
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self.client.create_collection(
                    name=name,
                    embedding_function=self.embedding_function,
                    metadata=metadata or {}
                )
            )
            logger.info("Created ChromaDB collection", collection=name)
            return True
        except Exception as e:
            logger.error("Failed to create collection", collection=name, error=str(e))
            return False
    
    async def get_or_create_collection(
        self,
        name: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Get existing collection or create if it doesn't exist.
        
        Args:
            name: Collection name
            metadata: Optional collection metadata
            
        Returns:
            ChromaDB collection object
        """
        try:
            loop = asyncio.get_event_loop()
            collection = await loop.run_in_executor(
                None,
                lambda: self.client.get_or_create_collection(
                    name=name,
                    embedding_function=self.embedding_function,
                    metadata=metadata or {"created_by": "oracle"}
                )
            )
            return collection
        except Exception as e:
            logger.error("Failed to get/create collection", collection=name, error=str(e))
            raise OracleException(
                message=f"Failed to access collection {name}: {str(e)}",
                error_code=ErrorCode.VECTOR_DB_ERROR
            )
    
    def chunk_text(
        self,
        text: str,
        chunk_size: int = 1000,
        chunk_overlap: int = 200
    ) -> List[str]:
        """Split text into overlapping chunks.
        
        Args:
            text: Text to chunk
            chunk_size: Maximum characters per chunk
            chunk_overlap: Overlap between consecutive chunks
            
        Returns:
            List of text chunks
        """
        if not text or not text.strip():
            return []
        
        if len(text) <= chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            
            # Try to break at sentence boundary if possible
            if end < len(text):
                # Look for sentence endings within the last 100 characters
                sentence_end = text.rfind('.', start + chunk_size - 100, end)
                if sentence_end > start:
                    end = sentence_end + 1
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            # Move start position with overlap
            start = max(start + 1, end - chunk_overlap)
            
            # Prevent infinite loop
            if start >= len(text):
                break
        
        return chunks
    
    async def add_documents(
        self,
        documents: List[str],
        metadatas: List[Dict[str, Any]],
        ids: List[str],
        collection_name: Optional[str] = None
    ) -> int:
        """Add documents to the vector database.
        
        Args:
            documents: List of document texts
            metadatas: List of metadata dictionaries
            ids: List of unique document IDs
            collection_name: Collection name (uses default if None)
            
        Returns:
            Number of documents added
        """
        if not documents or len(documents) != len(metadatas) or len(documents) != len(ids):
            raise ValueError("Documents, metadatas, and ids must have the same length")
        
        collection_name = collection_name or self.collection_name
        
        try:
            collection = await self.get_or_create_collection(collection_name)
            
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: collection.add(
                    documents=documents,
                    metadatas=metadatas,
                    ids=ids
                )
            )
            
            logger.info(
                "Added documents to ChromaDB",
                collection=collection_name,
                count=len(documents)
            )
            return len(documents)
            
        except Exception as e:
            logger.error(
                "Failed to add documents to ChromaDB",
                collection=collection_name,
                error=str(e)
            )
            raise OracleException(
                message=f"Failed to add documents: {str(e)}",
                error_code=ErrorCode.VECTOR_DB_ERROR
            )
    
    async def add_document_chunks(
        self,
        text: str,
        metadata: Dict[str, Any],
        document_id: str,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        collection_name: Optional[str] = None
    ) -> int:
        """Add a document as chunks to the vector database.
        
        Args:
            text: Document text to chunk and add
            metadata: Base metadata for the document
            document_id: Unique document identifier
            chunk_size: Maximum characters per chunk
            chunk_overlap: Overlap between consecutive chunks
            collection_name: Collection name (uses default if None)
            
        Returns:
            Number of chunks created
        """
        chunks = self.chunk_text(text, chunk_size, chunk_overlap)
        
        if not chunks:
            return 0
        
        # Create chunk IDs and metadata
        chunk_ids = []
        chunk_metadatas = []
        
        for i, chunk in enumerate(chunks):
            chunk_id = f"{document_id}_chunk_{i}"
            chunk_metadata = {
                **metadata,
                "chunk_index": i,
                "total_chunks": len(chunks),
                "chunk_size": len(chunk),
                "parent_document_id": document_id
            }
            
            chunk_ids.append(chunk_id)
            chunk_metadatas.append(chunk_metadata)
        
        await self.add_documents(
            documents=chunks,
            metadatas=chunk_metadatas,
            ids=chunk_ids,
            collection_name=collection_name
        )
        
        return len(chunks)
    
    async def similarity_search(
        self,
        query: str,
        n_results: int = 5,
        where: Optional[Dict[str, Any]] = None,
        collection_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Perform similarity search on the vector database.
        
        Args:
            query: Search query text
            n_results: Maximum number of results to return
            where: Optional metadata filter
            collection_name: Collection name (uses default if None)
            
        Returns:
            List of search results with documents, metadata, and distances
        """
        collection_name = collection_name or self.collection_name
        
        try:
            collection = await self.get_or_create_collection(collection_name)
            
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                None,
                lambda: collection.query(
                    query_texts=[query],
                    n_results=n_results,
                    where=where
                )
            )
            
            # Format results
            formatted_results = []
            if results['documents'] and results['documents'][0]:
                for i in range(len(results['documents'][0])):
                    result = {
                        'document': results['documents'][0][i],
                        'metadata': results['metadatas'][0][i] if results['metadatas'] else {},
                        'distance': results['distances'][0][i] if results['distances'] else 0.0,
                        'id': results['ids'][0][i] if results['ids'] else f"result_{i}",
                        'similarity_score': 1.0 - (results['distances'][0][i] if results['distances'] else 0.0)
                    }
                    formatted_results.append(result)
            
            logger.debug(
                "Performed similarity search",
                collection=collection_name,
                query_length=len(query),
                results_count=len(formatted_results)
            )
            
            return formatted_results
            
        except Exception as e:
            logger.error(
                "Similarity search failed",
                collection=collection_name,
                error=str(e)
            )
            raise OracleException(
                message=f"Similarity search failed: {str(e)}",
                error_code=ErrorCode.VECTOR_DB_ERROR
            )
    
    async def delete_documents(
        self,
        ids: List[str],
        collection_name: Optional[str] = None
    ) -> bool:
        """Delete documents from the vector database.
        
        Args:
            ids: List of document IDs to delete
            collection_name: Collection name (uses default if None)
            
        Returns:
            True if deletion was successful
        """
        collection_name = collection_name or self.collection_name
        
        try:
            collection = await self.get_or_create_collection(collection_name)
            
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: collection.delete(ids=ids)
            )
            
            logger.info(
                "Deleted documents from ChromaDB",
                collection=collection_name,
                count=len(ids)
            )
            return True
            
        except Exception as e:
            logger.error(
                "Failed to delete documents",
                collection=collection_name,
                error=str(e)
            )
            return False
    
    async def get_collection_stats(
        self,
        collection_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get statistics for a collection.
        
        Args:
            collection_name: Collection name (uses default if None)
            
        Returns:
            Collection statistics
        """
        collection_name = collection_name or self.collection_name
        
        try:
            collection = await self.get_or_create_collection(collection_name)
            
            loop = asyncio.get_event_loop()
            count = await loop.run_in_executor(None, collection.count)
            
            return {
                "name": collection_name,
                "document_count": count,
                "embedding_model": self.embedding_model_name
            }
            
        except Exception as e:
            logger.error(
                "Failed to get collection stats",
                collection=collection_name,
                error=str(e)
            )
            return {
                "name": collection_name,
                "document_count": 0,
                "error": str(e)
            }
    
    def generate_document_id(self, content: str, metadata: Dict[str, Any]) -> str:
        """Generate a unique document ID based on content and metadata.
        
        Args:
            content: Document content
            metadata: Document metadata
            
        Returns:
            Unique document ID
        """
        # Create a hash from content and key metadata
        hash_input = f"{content[:1000]}{metadata.get('filename', '')}{metadata.get('source', '')}"
        return hashlib.md5(hash_input.encode()).hexdigest()