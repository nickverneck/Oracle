"""Chat endpoint implementation."""

import time
from typing import Optional
import structlog
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse

from ...models.chat import ChatRequest, ChatResponse, Source
from ...models.errors import ModelClientError
from ...services.conversation import ConversationManager
from ...services.knowledge import KnowledgeRetrievalService
from ...clients.model_manager import ModelManager
from ...core.config import get_settings

logger = structlog.get_logger(__name__)

router = APIRouter()

# Global service instances (will be properly initialized via dependency injection)
conversation_manager: Optional[ConversationManager] = None
knowledge_service: Optional[KnowledgeRetrievalService] = None
model_manager: Optional[ModelManager] = None


def get_conversation_manager() -> ConversationManager:
    """Get conversation manager instance."""
    global conversation_manager
    if conversation_manager is None:
        conversation_manager = ConversationManager(max_history_length=10)
    return conversation_manager


def get_knowledge_service() -> KnowledgeRetrievalService:
    """Get knowledge retrieval service instance."""
    global knowledge_service
    if knowledge_service is None:
        settings = get_settings()
        config = {
            "neo4j": {
                "uri": getattr(settings, "NEO4J_URI", "bolt://localhost:7687"),
                "username": getattr(settings, "NEO4J_USERNAME", "neo4j"),
                "password": getattr(settings, "NEO4J_PASSWORD", "password")
            },
            "chromadb": {
                "host": getattr(settings, "CHROMADB_HOST", "localhost"),
                "port": getattr(settings, "CHROMADB_PORT", 8000)
            },
            "retrieval": {
                "max_graph_results": 5,
                "max_vector_results": 5,
                "similarity_threshold": 0.7
            }
        }
        knowledge_service = KnowledgeRetrievalService(config)
    return knowledge_service


def get_model_manager() -> ModelManager:
    """Get model manager instance."""
    global model_manager
    if model_manager is None:
        settings = get_settings()
        config = {
            "vllm": {
                "base_url": getattr(settings, "VLLM_BASE_URL", "http://localhost:8001"),
                "api_key": getattr(settings, "VLLM_API_KEY", ""),
                "model": getattr(settings, "VLLM_MODEL", "microsoft/DialoGPT-medium")
            },
            "ollama": {
                "base_url": getattr(settings, "OLLAMA_BASE_URL", "http://localhost:11434"),
                "model": getattr(settings, "OLLAMA_MODEL", "llama2")
            },
            "gemini": {
                "api_key": getattr(settings, "GEMINI_API_KEY", ""),
                "model": getattr(settings, "GEMINI_MODEL", "gemini-pro")
            },
            "fallback_order": ["vllm", "ollama", "gemini"]
        }
        model_manager = ModelManager(config)
    return model_manager


@router.post("/", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    background_tasks: BackgroundTasks,
    conversation_mgr: ConversationManager = Depends(get_conversation_manager),
    knowledge_svc: KnowledgeRetrievalService = Depends(get_knowledge_service),
    model_mgr: ModelManager = Depends(get_model_manager)
) -> ChatResponse:
    """Handle chat requests with knowledge integration.
    
    This endpoint:
    1. Validates the incoming chat request
    2. Retrieves relevant knowledge from graph and vector databases
    3. Generates a response using the configured AI model with fallback
    4. Manages conversation context and history
    5. Returns a structured response with sources and confidence scores
    """
    start_time = time.time()
    
    try:
        user_message = request.messages[-1]["content"]
        logger.info(
            "Processing chat request",
            message_length=len(user_message),
            provider=request.provider.name,
            include_sources=request.include_sources
        )
        
        # Get or create conversation context
        conversation_id = request.context.get("conversation_id") if request.context else None
        if conversation_id:
            context = conversation_mgr.get_conversation(conversation_id)
            if not context:
                logger.warning("Conversation not found, creating new one", conversation_id=conversation_id)
                conversation_id = conversation_mgr.create_conversation(conversation_id)
        else:
            conversation_id = conversation_mgr.create_conversation()
            logger.info("Created new conversation", conversation_id=conversation_id)
        
        # Add user message to conversation history
        conversation_mgr.add_message(
            conversation_id=conversation_id,
            role="user",
            content=user_message,
            metadata={"provider": request.provider.dict()}
        )
        
        # Retrieve knowledge sources if requested
        sources = []
        if request.include_sources:
            try:
                sources = await knowledge_svc.retrieve_knowledge(
                    query=user_message,
                    max_sources=request.max_sources,
                    include_graph=True,
                    include_vector=True
                )
                logger.info("Retrieved knowledge sources", source_count=len(sources))
            except Exception as e:
                logger.warning("Knowledge retrieval failed", error=str(e))
                # Continue without sources rather than failing the entire request
        
        # Build context-aware prompt
        context_prompt = conversation_mgr.build_context_prompt(
            conversation_id=conversation_id,
            current_message=user_message,
            include_history=True,
            max_context_messages=5
        )
        
        # Add knowledge context to prompt if sources available
        if sources:
            knowledge_context = "\n\nRelevant knowledge:\n"
            for i, source in enumerate(sources[:3], 1):  # Limit to top 3 sources for prompt
                knowledge_context += f"{i}. {source.content[:200]}...\n"
            context_prompt += knowledge_context
        
        # Generate response using model manager with fallback
        try:
            model_response = await model_mgr.generate(
                prompt=context_prompt,
                max_tokens=1000,
                temperature=0.7,
                preferred_provider=request.provider.type,
                provider_config=request.provider.config.dict()
            )
            
            logger.info(
                "Generated model response",
                model=model_response.model_used,
                tokens=model_response.usage.get("total_tokens") if model_response.usage else None,
                response_time=model_response.response_time
            )
            
        except ModelClientError as e:
            logger.error("All model providers failed", error=str(e))
            raise HTTPException(
                status_code=503,
                detail={
                    "error": "Model service unavailable",
                    "message": "All AI model providers are currently unavailable. Please try again later.",
                    "details": str(e)
                }
            )
        
        # Calculate confidence score based on various factors
        confidence = _calculate_confidence_score(
            model_response=model_response,
            sources=sources,
            conversation_length=len(conversation_mgr.get_conversation_history(conversation_id))
        )
        
        # Create response
        chat_response = ChatResponse(
            status="success",
            response=model_response.content,
            confidence=confidence,
            sources=sources,
            model_used=model_response.model_used,
            tokens_used=model_response.usage.get("total_tokens") if model_response.usage else None,
            processing_time=time.time() - start_time
        )
        
        # Add assistant response to conversation history (in background)
        background_tasks.add_task(
            conversation_mgr.add_message,
            conversation_id=conversation_id,
            role="assistant",
            content=model_response.content,
            metadata={
                "model": model_response.model_used,
                "confidence": confidence,
                "sources_count": len(sources),
                "tokens_used": model_response.usage.get("total_tokens") if model_response.usage else None
            }
        )
        
        logger.info(
            "Chat request completed successfully",
            conversation_id=conversation_id,
            response_length=len(model_response.content),
            confidence=confidence,
            total_time=chat_response.processing_time
        )
        
        return chat_response
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error("Unexpected error in chat endpoint", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Internal server error",
                "message": "An unexpected error occurred while processing your request.",
                "details": str(e)  # Always include details for now
            }
        )


@router.get("/conversations/{conversation_id}/history")
async def get_conversation_history(
    conversation_id: str,
    limit: Optional[int] = None,
    conversation_mgr: ConversationManager = Depends(get_conversation_manager)
):
    """Get conversation history for a specific conversation."""
    try:
        history = conversation_mgr.get_conversation_history(conversation_id, limit)
        
        if not history and not conversation_mgr.get_conversation(conversation_id):
            raise HTTPException(
                status_code=404,
                detail=f"Conversation {conversation_id} not found"
            )
        
        return {
            "conversation_id": conversation_id,
            "messages": history,
            "message_count": len(history)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error retrieving conversation history", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve conversation history"
        )


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    conversation_mgr: ConversationManager = Depends(get_conversation_manager)
):
    """Delete a conversation and its history."""
    try:
        deleted = conversation_mgr.delete_conversation(conversation_id)
        
        if not deleted:
            raise HTTPException(
                status_code=404,
                detail=f"Conversation {conversation_id} not found"
            )
        
        return {
            "message": f"Conversation {conversation_id} deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error deleting conversation", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to delete conversation"
        )


@router.get("/health")
async def chat_health_check(
    knowledge_svc: KnowledgeRetrievalService = Depends(get_knowledge_service),
    model_mgr: ModelManager = Depends(get_model_manager)
):
    """Health check for chat service and its dependencies."""
    try:
        # Check knowledge service health
        knowledge_health = await knowledge_svc.health_check()
        
        # Check model manager health
        model_health = await model_mgr.health_check()
        
        # Overall health status
        knowledge_service_healthy = knowledge_health.get("knowledge_service", False)
        any_model_healthy = any(model_health.values()) if model_health else False
        all_healthy = knowledge_service_healthy and any_model_healthy
        
        status_code = 200 if all_healthy else 503
        
        return JSONResponse(
            status_code=status_code,
            content={
                "status": "healthy" if all_healthy else "degraded",
                "services": {
                    "chat_endpoint": True,
                    "knowledge_retrieval": knowledge_health,
                    "model_providers": model_health
                },
                "timestamp": time.time()
            }
        )
        
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": time.time()
            }
        )


def _calculate_confidence_score(
    model_response,
    sources: list[Source],
    conversation_length: int
) -> float:
    """Calculate confidence score for the response.
    
    Args:
        model_response: Response from the model
        sources: Knowledge sources used
        conversation_length: Length of conversation history
        
    Returns:
        Confidence score between 0.0 and 1.0
    """
    base_confidence = 0.7  # Base confidence for any response
    
    # Boost confidence if we have high-quality knowledge sources
    if sources:
        avg_source_relevance = sum(s.relevance_score for s in sources) / len(sources)
        source_boost = min(0.2, avg_source_relevance * 0.3)
        base_confidence += source_boost
    
    # Slight boost for longer conversations (more context)
    context_boost = min(0.1, conversation_length * 0.01)
    base_confidence += context_boost
    
    # Ensure confidence is within valid range
    return min(1.0, max(0.0, base_confidence))