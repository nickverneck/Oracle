"""Entity extraction and relationship mapping for knowledge graph construction."""

import re
import logging
from typing import Dict, List, Set, Tuple, Optional, Any
from dataclasses import dataclass
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class ExtractedEntity:
    """Represents an extracted entity from text."""
    
    name: str
    entity_type: str
    confidence: float
    context: str
    start_pos: int
    end_pos: int
    properties: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.properties is None:
            self.properties = {}


@dataclass
class ExtractedRelationship:
    """Represents an extracted relationship between entities."""
    
    source_entity: str
    target_entity: str
    relationship_type: str
    confidence: float
    context: str
    properties: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.properties is None:
            self.properties = {}


class EntityExtractor:
    """Extracts entities and relationships from text using rule-based and pattern matching."""
    
    def __init__(self):
        """Initialize the entity extractor with predefined patterns."""
        self.entity_patterns = self._build_entity_patterns()
        self.relationship_patterns = self._build_relationship_patterns()
        self.stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
            'should', 'may', 'might', 'must', 'can', 'this', 'that', 'these', 'those'
        }
    
    def _build_entity_patterns(self) -> Dict[str, List[str]]:
        """Build regex patterns for different entity types.
        
        Returns:
            Dictionary mapping entity types to regex patterns
        """
        return {
            'PRODUCT': [
                r'\b[A-Z][a-zA-Z0-9\-_]*\s*(?:v\d+(?:\.\d+)*|version\s*\d+(?:\.\d+)*|[Vv]\d+(?:\.\d+)*)\b',
                r'\b[A-Z][a-zA-Z0-9\-_]*\s*(?:Pro|Premium|Enterprise|Standard|Basic|Lite)\b',
                r'\b[A-Z][a-zA-Z0-9\-_]*\s*(?:Server|Client|Desktop|Mobile|Web|API)\b',
            ],
            'ERROR': [
                r'\b(?:Error|Exception|Failure|Issue|Problem|Bug)\s*(?:Code\s*)?[A-Z0-9\-_]+\b',
                r'\b[A-Z][a-zA-Z]*(?:Error|Exception|Failure)\b',
                r'\berror\s*(?:code\s*)?:?\s*[A-Z0-9\-_]+\b',
            ],
            'COMPONENT': [
                r'\b[A-Z][a-zA-Z0-9]*(?:Service|Manager|Handler|Controller|Module|Component|Engine|Driver)\b',
                r'\b(?:database|server|client|api|service|module|component|library|framework)\b',
            ],
            'PROCESS': [
                r'\b(?:installation|configuration|setup|deployment|migration|backup|restore|update|upgrade)\b',
                r'\b(?:login|authentication|authorization|validation|verification|synchronization)\b',
            ],
            'TECHNOLOGY': [
                r'\b(?:SQL|HTTP|HTTPS|TCP|UDP|REST|SOAP|JSON|XML|HTML|CSS|JavaScript|Python|Java|C\+\+|C#)\b',
                r'\b(?:Windows|Linux|macOS|Android|iOS|Docker|Kubernetes|AWS|Azure|GCP)\b',
            ],
            'FILE': [
                r'\b[a-zA-Z0-9\-_]+\.(?:exe|dll|so|dylib|jar|war|zip|tar|gz|log|txt|xml|json|yaml|yml|ini|conf|cfg)\b',
                r'\b(?:config|configuration|settings|preferences)\.(?:xml|json|yaml|yml|ini|conf|cfg)\b',
            ],
            'LOCATION': [
                r'\b[A-Z]:\\(?:[^\\/:*?"<>|\r\n]+\\)*[^\\/:*?"<>|\r\n]*\b',  # Windows paths
                r'\b/(?:[^/\s]+/)*[^/\s]*\b',  # Unix paths
                r'\b(?:C:|D:|E:)\\[^\s]*\b',  # Windows drive paths
            ]
        }
    
    def _build_relationship_patterns(self) -> List[Dict[str, str]]:
        """Build patterns for extracting relationships between entities.
        
        Returns:
            List of relationship pattern dictionaries
        """
        return [
            {
                'pattern': r'(.+?)\s+(?:causes?|triggers?|leads?\s+to|results?\s+in)\s+(.+?)(?:\.|$)',
                'type': 'CAUSES',
                'confidence': 0.8
            },
            {
                'pattern': r'(.+?)\s+(?:requires?|needs?|depends?\s+on)\s+(.+?)(?:\.|$)',
                'type': 'REQUIRES',
                'confidence': 0.7
            },
            {
                'pattern': r'(.+?)\s+(?:is\s+part\s+of|belongs\s+to|is\s+in)\s+(.+?)(?:\.|$)',
                'type': 'PART_OF',
                'confidence': 0.7
            },
            {
                'pattern': r'(.+?)\s+(?:connects?\s+to|communicates?\s+with|interfaces?\s+with)\s+(.+?)(?:\.|$)',
                'type': 'CONNECTS_TO',
                'confidence': 0.6
            },
            {
                'pattern': r'(.+?)\s+(?:contains?|includes?|has)\s+(.+?)(?:\.|$)',
                'type': 'CONTAINS',
                'confidence': 0.6
            },
            {
                'pattern': r'(.+?)\s+(?:is\s+similar\s+to|is\s+like|resembles?)\s+(.+?)(?:\.|$)',
                'type': 'SIMILAR_TO',
                'confidence': 0.5
            }
        ]
    
    def extract_entities(self, text: str, min_confidence: float = 0.5) -> List[ExtractedEntity]:
        """Extract entities from text using pattern matching.
        
        Args:
            text: Input text to extract entities from
            min_confidence: Minimum confidence threshold for entities
            
        Returns:
            List of ExtractedEntity objects
        """
        entities = []
        text_lower = text.lower()
        
        for entity_type, patterns in self.entity_patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                
                for match in matches:
                    entity_name = match.group().strip()
                    
                    # Skip if entity is too short or is a stop word
                    if len(entity_name) < 2 or entity_name.lower() in self.stop_words:
                        continue
                    
                    # Calculate confidence based on pattern specificity and context
                    confidence = self._calculate_entity_confidence(
                        entity_name, entity_type, text, match.start(), match.end()
                    )
                    
                    if confidence >= min_confidence:
                        # Extract context around the entity
                        context_start = max(0, match.start() - 50)
                        context_end = min(len(text), match.end() + 50)
                        context = text[context_start:context_end].strip()
                        
                        entities.append(ExtractedEntity(
                            name=entity_name,
                            entity_type=entity_type,
                            confidence=confidence,
                            context=context,
                            start_pos=match.start(),
                            end_pos=match.end(),
                            properties={
                                'extraction_method': 'pattern_matching',
                                'pattern_type': entity_type.lower()
                            }
                        ))
        
        # Remove duplicates and overlapping entities
        entities = self._deduplicate_entities(entities)
        
        return sorted(entities, key=lambda x: x.confidence, reverse=True)
    
    def extract_relationships(
        self,
        text: str,
        entities: List[ExtractedEntity],
        min_confidence: float = 0.4
    ) -> List[ExtractedRelationship]:
        """Extract relationships between entities from text.
        
        Args:
            text: Input text to extract relationships from
            entities: List of extracted entities to find relationships between
            min_confidence: Minimum confidence threshold for relationships
            
        Returns:
            List of ExtractedRelationship objects
        """
        relationships = []
        sentences = self._split_into_sentences(text)
        
        # Create entity lookup for quick access
        entity_lookup = {entity.name.lower(): entity for entity in entities}
        
        for sentence in sentences:
            sentence_lower = sentence.lower()
            
            # Find entities mentioned in this sentence
            sentence_entities = []
            for entity in entities:
                if entity.name.lower() in sentence_lower:
                    sentence_entities.append(entity)
            
            # Skip if less than 2 entities in sentence
            if len(sentence_entities) < 2:
                continue
            
            # Try to extract relationships using patterns
            for pattern_info in self.relationship_patterns:
                pattern = pattern_info['pattern']
                rel_type = pattern_info['type']
                base_confidence = pattern_info['confidence']
                
                matches = re.finditer(pattern, sentence, re.IGNORECASE)
                
                for match in matches:
                    source_text = match.group(1).strip()
                    target_text = match.group(2).strip()
                    
                    # Find matching entities
                    source_entity = self._find_matching_entity(source_text, sentence_entities)
                    target_entity = self._find_matching_entity(target_text, sentence_entities)
                    
                    if source_entity and target_entity and source_entity != target_entity:
                        confidence = self._calculate_relationship_confidence(
                            source_entity, target_entity, rel_type, sentence, base_confidence
                        )
                        
                        if confidence >= min_confidence:
                            relationships.append(ExtractedRelationship(
                                source_entity=source_entity.name,
                                target_entity=target_entity.name,
                                relationship_type=rel_type,
                                confidence=confidence,
                                context=sentence,
                                properties={
                                    'extraction_method': 'pattern_matching',
                                    'sentence_context': sentence
                                }
                            ))
        
        # Add co-occurrence relationships for entities in the same sentence
        relationships.extend(self._extract_cooccurrence_relationships(
            entities, sentences, min_confidence
        ))
        
        return self._deduplicate_relationships(relationships)
    
    def _calculate_entity_confidence(
        self,
        entity_name: str,
        entity_type: str,
        text: str,
        start_pos: int,
        end_pos: int
    ) -> float:
        """Calculate confidence score for an extracted entity.
        
        Args:
            entity_name: Name of the extracted entity
            entity_type: Type of the entity
            text: Full text context
            start_pos: Start position of entity in text
            end_pos: End position of entity in text
            
        Returns:
            Confidence score between 0 and 1
        """
        confidence = 0.5  # Base confidence
        
        # Boost confidence for longer entities
        if len(entity_name) > 10:
            confidence += 0.1
        elif len(entity_name) > 5:
            confidence += 0.05
        
        # Boost confidence for entities with specific patterns
        if re.search(r'\d+', entity_name):  # Contains numbers
            confidence += 0.1
        
        if re.search(r'[A-Z]{2,}', entity_name):  # Contains uppercase sequences
            confidence += 0.1
        
        # Boost confidence based on context
        context_start = max(0, start_pos - 20)
        context_end = min(len(text), end_pos + 20)
        context = text[context_start:context_end].lower()
        
        # Look for contextual indicators
        context_indicators = {
            'PRODUCT': ['product', 'software', 'application', 'system', 'tool'],
            'ERROR': ['error', 'exception', 'failure', 'issue', 'problem'],
            'COMPONENT': ['component', 'module', 'service', 'library'],
            'PROCESS': ['process', 'procedure', 'step', 'operation'],
            'TECHNOLOGY': ['technology', 'framework', 'language', 'platform'],
            'FILE': ['file', 'document', 'config', 'log'],
            'LOCATION': ['path', 'directory', 'folder', 'location']
        }
        
        if entity_type in context_indicators:
            for indicator in context_indicators[entity_type]:
                if indicator in context:
                    confidence += 0.05
                    break
        
        return min(confidence, 1.0)
    
    def _calculate_relationship_confidence(
        self,
        source_entity: ExtractedEntity,
        target_entity: ExtractedEntity,
        rel_type: str,
        context: str,
        base_confidence: float
    ) -> float:
        """Calculate confidence score for an extracted relationship.
        
        Args:
            source_entity: Source entity of the relationship
            target_entity: Target entity of the relationship
            rel_type: Type of relationship
            context: Context sentence
            base_confidence: Base confidence from pattern matching
            
        Returns:
            Confidence score between 0 and 1
        """
        confidence = base_confidence
        
        # Boost confidence if entities are of compatible types
        compatible_types = {
            'CAUSES': [('ERROR', 'ERROR'), ('PROCESS', 'ERROR'), ('COMPONENT', 'ERROR')],
            'REQUIRES': [('PROCESS', 'COMPONENT'), ('COMPONENT', 'TECHNOLOGY'), ('PRODUCT', 'COMPONENT')],
            'PART_OF': [('COMPONENT', 'PRODUCT'), ('FILE', 'COMPONENT'), ('PROCESS', 'PRODUCT')],
            'CONNECTS_TO': [('COMPONENT', 'COMPONENT'), ('PRODUCT', 'PRODUCT')],
            'CONTAINS': [('PRODUCT', 'COMPONENT'), ('COMPONENT', 'FILE')],
        }
        
        if rel_type in compatible_types:
            entity_pair = (source_entity.entity_type, target_entity.entity_type)
            if entity_pair in compatible_types[rel_type]:
                confidence += 0.1
        
        # Boost confidence for high-confidence entities
        avg_entity_confidence = (source_entity.confidence + target_entity.confidence) / 2
        confidence += (avg_entity_confidence - 0.5) * 0.2
        
        return min(confidence, 1.0)
    
    def _find_matching_entity(
        self,
        text: str,
        entities: List[ExtractedEntity]
    ) -> Optional[ExtractedEntity]:
        """Find the best matching entity for a text snippet.
        
        Args:
            text: Text to match against entities
            entities: List of entities to search in
            
        Returns:
            Best matching ExtractedEntity or None
        """
        text_lower = text.lower().strip()
        
        # Exact match first
        for entity in entities:
            if entity.name.lower() == text_lower:
                return entity
        
        # Partial match
        for entity in entities:
            if entity.name.lower() in text_lower or text_lower in entity.name.lower():
                return entity
        
        return None
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences.
        
        Args:
            text: Input text to split
            
        Returns:
            List of sentences
        """
        # Simple sentence splitting - can be enhanced with NLTK or spaCy
        sentences = re.split(r'[.!?]+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _deduplicate_entities(self, entities: List[ExtractedEntity]) -> List[ExtractedEntity]:
        """Remove duplicate and overlapping entities.
        
        Args:
            entities: List of entities to deduplicate
            
        Returns:
            Deduplicated list of entities
        """
        # Sort by confidence descending
        entities.sort(key=lambda x: x.confidence, reverse=True)
        
        deduplicated = []
        used_positions = set()
        
        for entity in entities:
            # Check for overlap with already selected entities
            overlap = False
            for pos in range(entity.start_pos, entity.end_pos):
                if pos in used_positions:
                    overlap = True
                    break
            
            if not overlap:
                deduplicated.append(entity)
                for pos in range(entity.start_pos, entity.end_pos):
                    used_positions.add(pos)
        
        return deduplicated
    
    def _deduplicate_relationships(
        self,
        relationships: List[ExtractedRelationship]
    ) -> List[ExtractedRelationship]:
        """Remove duplicate relationships.
        
        Args:
            relationships: List of relationships to deduplicate
            
        Returns:
            Deduplicated list of relationships
        """
        seen = set()
        deduplicated = []
        
        for rel in relationships:
            # Create a unique key for the relationship
            key = (rel.source_entity.lower(), rel.target_entity.lower(), rel.relationship_type)
            
            if key not in seen:
                seen.add(key)
                deduplicated.append(rel)
        
        return sorted(deduplicated, key=lambda x: x.confidence, reverse=True)
    
    def _extract_cooccurrence_relationships(
        self,
        entities: List[ExtractedEntity],
        sentences: List[str],
        min_confidence: float
    ) -> List[ExtractedRelationship]:
        """Extract co-occurrence relationships between entities in the same sentence.
        
        Args:
            entities: List of extracted entities
            sentences: List of sentences from the text
            min_confidence: Minimum confidence threshold
            
        Returns:
            List of co-occurrence relationships
        """
        relationships = []
        
        for sentence in sentences:
            sentence_lower = sentence.lower()
            
            # Find entities in this sentence
            sentence_entities = []
            for entity in entities:
                if entity.name.lower() in sentence_lower:
                    sentence_entities.append(entity)
            
            # Create co-occurrence relationships
            for i, entity1 in enumerate(sentence_entities):
                for entity2 in sentence_entities[i+1:]:
                    confidence = 0.3  # Base confidence for co-occurrence
                    
                    # Boost confidence based on entity types and sentence length
                    if len(sentence.split()) < 20:  # Short sentence
                        confidence += 0.1
                    
                    if confidence >= min_confidence:
                        relationships.append(ExtractedRelationship(
                            source_entity=entity1.name,
                            target_entity=entity2.name,
                            relationship_type='CO_OCCURS_WITH',
                            confidence=confidence,
                            context=sentence,
                            properties={
                                'extraction_method': 'co_occurrence',
                                'sentence_length': len(sentence.split())
                            }
                        ))
        
        return relationships