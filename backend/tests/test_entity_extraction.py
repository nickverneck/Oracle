"""Unit tests for entity extraction service."""

import pytest
from typing import List

from oracle.services.entity_extraction import (
    EntityExtractor,
    ExtractedEntity,
    ExtractedRelationship
)


class TestEntityExtractor:
    """Test cases for EntityExtractor."""
    
    @pytest.fixture
    def extractor(self) -> EntityExtractor:
        """Create an EntityExtractor instance for testing."""
        return EntityExtractor()
    
    def test_extract_product_entities(self, extractor: EntityExtractor):
        """Test extraction of product entities."""
        text = "Oracle Database v19.3 and MySQL Server 8.0 are both database products."
        
        entities = extractor.extract_entities(text, min_confidence=0.3)
        
        product_entities = [e for e in entities if e.entity_type == 'PRODUCT']
        assert len(product_entities) >= 1
        
        # Check for version patterns
        version_entities = [e for e in product_entities if 'v19.3' in e.name or '8.0' in e.name]
        assert len(version_entities) >= 1
    
    def test_extract_error_entities(self, extractor: EntityExtractor):
        """Test extraction of error entities."""
        text = "The system encountered Error Code 500 and a DatabaseConnectionException occurred."
        
        entities = extractor.extract_entities(text, min_confidence=0.3)
        
        error_entities = [e for e in entities if e.entity_type == 'ERROR']
        assert len(error_entities) >= 1
        
        # Check for specific error patterns
        error_names = [e.name for e in error_entities]
        assert any('500' in name or 'DatabaseConnectionException' in name for name in error_names)
    
    def test_extract_component_entities(self, extractor: EntityExtractor):
        """Test extraction of component entities."""
        text = "The AuthenticationService and DatabaseManager components handle user login."
        
        entities = extractor.extract_entities(text, min_confidence=0.3)
        
        component_entities = [e for e in entities if e.entity_type == 'COMPONENT']
        assert len(component_entities) >= 1
        
        component_names = [e.name for e in component_entities]
        assert any('Service' in name or 'Manager' in name for name in component_names)
    
    def test_extract_technology_entities(self, extractor: EntityExtractor):
        """Test extraction of technology entities."""
        text = "The application uses Python, JavaScript, and connects via HTTP to a REST API."
        
        entities = extractor.extract_entities(text, min_confidence=0.3)
        
        tech_entities = [e for e in entities if e.entity_type == 'TECHNOLOGY']
        assert len(tech_entities) >= 2
        
        tech_names = [e.name.lower() for e in tech_entities]
        assert 'python' in tech_names or 'javascript' in tech_names
        assert 'http' in tech_names or 'rest' in tech_names
    
    def test_extract_file_entities(self, extractor: EntityExtractor):
        """Test extraction of file entities."""
        text = "Check the config.xml file and review application.log for errors."
        
        entities = extractor.extract_entities(text, min_confidence=0.3)
        
        file_entities = [e for e in entities if e.entity_type == 'FILE']
        assert len(file_entities) >= 1
        
        file_names = [e.name for e in file_entities]
        assert any('.xml' in name or '.log' in name for name in file_names)
    
    def test_extract_location_entities(self, extractor: EntityExtractor):
        """Test extraction of location entities."""
        text = "The files are located at C:\\Program Files\\Oracle and /usr/local/bin/mysql."
        
        entities = extractor.extract_entities(text, min_confidence=0.3)
        
        location_entities = [e for e in entities if e.entity_type == 'LOCATION']
        assert len(location_entities) >= 1
        
        location_names = [e.name for e in location_entities]
        assert any('C:\\' in name or '/usr/' in name for name in location_names)
    
    def test_entity_confidence_calculation(self, extractor: EntityExtractor):
        """Test that entity confidence is calculated properly."""
        text = "The DatabaseConnectionError occurred in the AuthenticationService component."
        
        entities = extractor.extract_entities(text, min_confidence=0.1)
        
        # All entities should have confidence scores
        assert all(0.0 <= e.confidence <= 1.0 for e in entities)
        
        # Entities with more specific patterns should have higher confidence
        error_entities = [e for e in entities if e.entity_type == 'ERROR']
        if error_entities:
            assert any(e.confidence > 0.5 for e in error_entities)
    
    def test_entity_deduplication(self, extractor: EntityExtractor):
        """Test that overlapping entities are properly deduplicated."""
        text = "The Oracle Database Server v12.2 system is running."
        
        entities = extractor.extract_entities(text, min_confidence=0.3)
        
        # Check that we don't have overlapping entities
        for i, entity1 in enumerate(entities):
            for entity2 in entities[i+1:]:
                # Entities should not overlap in position
                assert not (entity1.start_pos < entity2.end_pos and entity2.start_pos < entity1.end_pos)
    
    def test_extract_causes_relationships(self, extractor: EntityExtractor):
        """Test extraction of causal relationships."""
        text = "The DatabaseConnectionError causes the AuthenticationService to fail."
        
        entities = extractor.extract_entities(text, min_confidence=0.3)
        relationships = extractor.extract_relationships(text, entities, min_confidence=0.3)
        
        causes_rels = [r for r in relationships if r.relationship_type == 'CAUSES']
        assert len(causes_rels) >= 1
        
        # Check that the relationship makes sense
        if causes_rels:
            rel = causes_rels[0]
            assert 'Error' in rel.source_entity or 'Service' in rel.target_entity
    
    def test_extract_requires_relationships(self, extractor: EntityExtractor):
        """Test extraction of requirement relationships."""
        text = "The installation process requires the Java Runtime Environment."
        
        entities = extractor.extract_entities(text, min_confidence=0.3)
        relationships = extractor.extract_relationships(text, entities, min_confidence=0.3)
        
        requires_rels = [r for r in relationships if r.relationship_type == 'REQUIRES']
        assert len(requires_rels) >= 1
        
        if requires_rels:
            rel = requires_rels[0]
            assert rel.confidence > 0.0
    
    def test_extract_part_of_relationships(self, extractor: EntityExtractor):
        """Test extraction of part-of relationships."""
        text = "The UserController is part of the AuthenticationService module."
        
        entities = extractor.extract_entities(text, min_confidence=0.3)
        relationships = extractor.extract_relationships(text, entities, min_confidence=0.3)
        
        part_of_rels = [r for r in relationships if r.relationship_type == 'PART_OF']
        assert len(part_of_rels) >= 1
        
        if part_of_rels:
            rel = part_of_rels[0]
            assert 'Controller' in rel.source_entity or 'Service' in rel.target_entity
    
    def test_extract_cooccurrence_relationships(self, extractor: EntityExtractor):
        """Test extraction of co-occurrence relationships."""
        text = "The Oracle Database and MySQL Server are both database systems."
        
        entities = extractor.extract_entities(text, min_confidence=0.3)
        relationships = extractor.extract_relationships(text, entities, min_confidence=0.2)
        
        cooccur_rels = [r for r in relationships if r.relationship_type == 'CO_OCCURS_WITH']
        assert len(cooccur_rels) >= 1
        
        if cooccur_rels:
            rel = cooccur_rels[0]
            assert rel.confidence > 0.0
            assert rel.source_entity != rel.target_entity
    
    def test_relationship_confidence_calculation(self, extractor: EntityExtractor):
        """Test that relationship confidence is calculated properly."""
        text = "The DatabaseError causes the system to crash and requires immediate attention."
        
        entities = extractor.extract_entities(text, min_confidence=0.3)
        relationships = extractor.extract_relationships(text, entities, min_confidence=0.1)
        
        # All relationships should have confidence scores
        assert all(0.0 <= r.confidence <= 1.0 for r in relationships)
        
        # Relationships with compatible entity types should have higher confidence
        causes_rels = [r for r in relationships if r.relationship_type == 'CAUSES']
        if causes_rels:
            assert any(r.confidence > 0.4 for r in causes_rels)
    
    def test_relationship_deduplication(self, extractor: EntityExtractor):
        """Test that duplicate relationships are properly removed."""
        text = "The service requires the database. The service needs the database connection."
        
        entities = extractor.extract_entities(text, min_confidence=0.3)
        relationships = extractor.extract_relationships(text, entities, min_confidence=0.3)
        
        # Check for duplicate relationships
        seen_relationships = set()
        for rel in relationships:
            key = (rel.source_entity.lower(), rel.target_entity.lower(), rel.relationship_type)
            assert key not in seen_relationships, f"Duplicate relationship found: {key}"
            seen_relationships.add(key)
    
    def test_complex_text_extraction(self, extractor: EntityExtractor):
        """Test entity and relationship extraction from complex text."""
        text = """
        The Oracle Database Server v19.3 encountered a ConnectionTimeoutError when trying to 
        connect to the AuthenticationService. This error causes the login process to fail.
        The system requires a restart of the DatabaseManager component to resolve the issue.
        Check the error.log file located at /var/log/oracle/ for more details.
        """
        
        entities = extractor.extract_entities(text, min_confidence=0.3)
        relationships = extractor.extract_relationships(text, entities, min_confidence=0.3)
        
        # Should extract multiple entity types
        entity_types = {e.entity_type for e in entities}
        assert len(entity_types) >= 3
        
        # Should extract multiple relationship types
        relationship_types = {r.relationship_type for r in relationships}
        assert len(relationship_types) >= 2
        
        # Should have reasonable number of entities and relationships
        assert len(entities) >= 5
        assert len(relationships) >= 3
    
    def test_empty_text_handling(self, extractor: EntityExtractor):
        """Test handling of empty or whitespace-only text."""
        empty_texts = ["", "   ", "\n\t", "   \n  \t  "]
        
        for text in empty_texts:
            entities = extractor.extract_entities(text)
            relationships = extractor.extract_relationships(text, entities)
            
            assert len(entities) == 0
            assert len(relationships) == 0
    
    def test_stop_words_filtering(self, extractor: EntityExtractor):
        """Test that stop words are properly filtered out."""
        text = "The and or but in on at to for of with by is are was were be been being have has had do does did will would could should may might must can this that these those"
        
        entities = extractor.extract_entities(text, min_confidence=0.1)
        
        # Should not extract stop words as entities
        entity_names = {e.name.lower() for e in entities}
        stop_words = extractor.stop_words
        
        # No stop words should be extracted as entities
        assert len(entity_names.intersection(stop_words)) == 0
    
    def test_minimum_confidence_filtering(self, extractor: EntityExtractor):
        """Test that entities below minimum confidence are filtered out."""
        text = "The system has various components and modules."
        
        # Extract with high confidence threshold
        high_conf_entities = extractor.extract_entities(text, min_confidence=0.8)
        
        # Extract with low confidence threshold
        low_conf_entities = extractor.extract_entities(text, min_confidence=0.1)
        
        # Should have fewer entities with high confidence threshold
        assert len(high_conf_entities) <= len(low_conf_entities)
        
        # All high confidence entities should meet the threshold
        assert all(e.confidence >= 0.8 for e in high_conf_entities)
        assert all(e.confidence >= 0.1 for e in low_conf_entities)


class TestExtractedEntity:
    """Test ExtractedEntity data class."""
    
    def test_extracted_entity_creation(self):
        """Test ExtractedEntity creation with all fields."""
        entity = ExtractedEntity(
            name="TestEntity",
            entity_type="TEST",
            confidence=0.8,
            context="This is a test entity in context",
            start_pos=10,
            end_pos=20,
            properties={"key": "value"}
        )
        
        assert entity.name == "TestEntity"
        assert entity.entity_type == "TEST"
        assert entity.confidence == 0.8
        assert entity.context == "This is a test entity in context"
        assert entity.start_pos == 10
        assert entity.end_pos == 20
        assert entity.properties == {"key": "value"}
    
    def test_extracted_entity_default_properties(self):
        """Test ExtractedEntity creation with default properties."""
        entity = ExtractedEntity(
            name="TestEntity",
            entity_type="TEST",
            confidence=0.8,
            context="context",
            start_pos=0,
            end_pos=10
        )
        
        assert entity.properties == {}


class TestExtractedRelationship:
    """Test ExtractedRelationship data class."""
    
    def test_extracted_relationship_creation(self):
        """Test ExtractedRelationship creation with all fields."""
        relationship = ExtractedRelationship(
            source_entity="Entity1",
            target_entity="Entity2",
            relationship_type="RELATES_TO",
            confidence=0.7,
            context="Entity1 relates to Entity2 in this context",
            properties={"strength": 0.9}
        )
        
        assert relationship.source_entity == "Entity1"
        assert relationship.target_entity == "Entity2"
        assert relationship.relationship_type == "RELATES_TO"
        assert relationship.confidence == 0.7
        assert relationship.context == "Entity1 relates to Entity2 in this context"
        assert relationship.properties == {"strength": 0.9}
    
    def test_extracted_relationship_default_properties(self):
        """Test ExtractedRelationship creation with default properties."""
        relationship = ExtractedRelationship(
            source_entity="Entity1",
            target_entity="Entity2",
            relationship_type="RELATES_TO",
            confidence=0.7,
            context="context"
        )
        
        assert relationship.properties == {}