"""
Service Mapping System

This module implements the service mapping system for cross-provider service
normalization in the multi-cloud cost analytics platform. It provides
functionality to map provider-specific services to unified categories and
supports custom mapping configurations per client.
"""

import json
import logging
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

from ..models.multi_cloud_models import CloudProvider, ServiceCategory, SERVICE_CATEGORY_MAPPING
from ..models.provider_models import ProviderType


logger = logging.getLogger(__name__)


class MappingConfidence(Enum):
    """Confidence levels for service mappings."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"


@dataclass
class ServiceMapping:
    """Individual service mapping entry."""
    provider_service_name: str
    unified_category: ServiceCategory
    confidence: MappingConfidence
    description: Optional[str] = None
    aliases: List[str] = field(default_factory=list)
    tags: Dict[str, str] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            'provider_service_name': self.provider_service_name,
            'unified_category': self.unified_category.value,
            'confidence': self.confidence.value,
            'description': self.description,
            'aliases': self.aliases,
            'tags': self.tags,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ServiceMapping':
        """Create ServiceMapping from dictionary."""
        return cls(
            provider_service_name=data['provider_service_name'],
            unified_category=ServiceCategory(data['unified_category']),
            confidence=MappingConfidence(data['confidence']),
            description=data.get('description'),
            aliases=data.get('aliases', []),
            tags=data.get('tags', {}),
            created_at=datetime.fromisoformat(data.get('created_at', datetime.utcnow().isoformat())),
            updated_at=datetime.fromisoformat(data.get('updated_at', datetime.utcnow().isoformat()))
        )


@dataclass
class CustomMappingRule:
    """Custom mapping rule for client-specific overrides."""
    client_id: str
    provider: CloudProvider
    service_pattern: str  # Can be exact match or regex
    target_category: ServiceCategory
    rule_type: str = "exact"  # "exact", "regex", "contains"
    priority: int = 100  # Higher priority rules override lower priority
    is_active: bool = True
    created_by: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            'client_id': self.client_id,
            'provider': self.provider.value,
            'service_pattern': self.service_pattern,
            'target_category': self.target_category.value,
            'rule_type': self.rule_type,
            'priority': self.priority,
            'is_active': self.is_active,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CustomMappingRule':
        """Create CustomMappingRule from dictionary."""
        return cls(
            client_id=data['client_id'],
            provider=CloudProvider(data['provider']),
            service_pattern=data['service_pattern'],
            target_category=ServiceCategory(data['target_category']),
            rule_type=data.get('rule_type', 'exact'),
            priority=data.get('priority', 100),
            is_active=data.get('is_active', True),
            created_by=data.get('created_by'),
            created_at=datetime.fromisoformat(data.get('created_at', datetime.utcnow().isoformat()))
        )


class ServiceMapper:
    """
    Service mapping system for cross-provider service normalization.
    
    This class provides functionality to:
    1. Map provider-specific services to unified categories
    2. Support custom mapping configurations per client
    3. Handle fuzzy matching and aliases
    4. Provide mapping confidence scores
    """
    
    def __init__(self):
        """Initialize the service mapper."""
        self.logger = logging.getLogger(f"{__name__}.ServiceMapper")
        self._base_mappings: Dict[CloudProvider, Dict[str, ServiceMapping]] = {}
        self._custom_rules: Dict[str, List[CustomMappingRule]] = {}  # client_id -> rules
        self._fuzzy_cache: Dict[str, ServiceMapping] = {}
        self._initialize_base_mappings()
    
    def _initialize_base_mappings(self):
        """Initialize base service mappings from the predefined mapping."""
        for provider, service_map in SERVICE_CATEGORY_MAPPING.items():
            self._base_mappings[provider] = {}
            
            for service_name, category in service_map.items():
                mapping = ServiceMapping(
                    provider_service_name=service_name,
                    unified_category=category,
                    confidence=MappingConfidence.HIGH,
                    description=f"Base mapping for {provider.value} {service_name}"
                )
                self._base_mappings[provider][service_name] = mapping
        
        self.logger.info(f"Initialized base mappings for {len(self._base_mappings)} providers")
    
    def map_service(
        self, 
        provider: CloudProvider, 
        service_name: str, 
        client_id: Optional[str] = None
    ) -> ServiceMapping:
        """
        Map a provider-specific service to a unified category.
        
        Args:
            provider: Cloud provider
            service_name: Provider-specific service name
            client_id: Optional client ID for custom mappings
            
        Returns:
            ServiceMapping with unified category and confidence
        """
        # 1. Check custom rules first (if client_id provided)
        if client_id:
            custom_mapping = self._apply_custom_rules(provider, service_name, client_id)
            if custom_mapping:
                return custom_mapping
        
        # 2. Check exact match in base mappings
        provider_mappings = self._base_mappings.get(provider, {})
        if service_name in provider_mappings:
            return provider_mappings[service_name]
        
        # 3. Try fuzzy matching
        fuzzy_mapping = self._fuzzy_match_service(provider, service_name)
        if fuzzy_mapping:
            return fuzzy_mapping
        
        # 4. Return default mapping with low confidence
        return ServiceMapping(
            provider_service_name=service_name,
            unified_category=ServiceCategory.OTHER,
            confidence=MappingConfidence.UNKNOWN,
            description=f"Unknown service mapping for {provider.value} {service_name}"
        )
    
    def _apply_custom_rules(
        self, 
        provider: CloudProvider, 
        service_name: str, 
        client_id: str
    ) -> Optional[ServiceMapping]:
        """
        Apply custom mapping rules for a specific client.
        
        Args:
            provider: Cloud provider
            service_name: Service name to map
            client_id: Client identifier
            
        Returns:
            ServiceMapping if custom rule matches, None otherwise
        """
        client_rules = self._custom_rules.get(client_id, [])
        
        # Sort rules by priority (highest first)
        sorted_rules = sorted(
            [rule for rule in client_rules if rule.provider == provider and rule.is_active],
            key=lambda r: r.priority,
            reverse=True
        )
        
        for rule in sorted_rules:
            if self._rule_matches(rule, service_name):
                return ServiceMapping(
                    provider_service_name=service_name,
                    unified_category=rule.target_category,
                    confidence=MappingConfidence.HIGH,
                    description=f"Custom mapping rule for client {client_id}",
                    tags={'custom_rule': 'true', 'client_id': client_id}
                )
        
        return None
    
    def _rule_matches(self, rule: CustomMappingRule, service_name: str) -> bool:
        """
        Check if a custom rule matches a service name.
        
        Args:
            rule: Custom mapping rule
            service_name: Service name to check
            
        Returns:
            True if rule matches, False otherwise
        """
        if rule.rule_type == "exact":
            return rule.service_pattern == service_name
        elif rule.rule_type == "contains":
            return rule.service_pattern.lower() in service_name.lower()
        elif rule.rule_type == "regex":
            import re
            try:
                return bool(re.search(rule.service_pattern, service_name, re.IGNORECASE))
            except re.error:
                self.logger.warning(f"Invalid regex pattern in rule: {rule.service_pattern}")
                return False
        
        return False
    
    def _fuzzy_match_service(
        self, 
        provider: CloudProvider, 
        service_name: str
    ) -> Optional[ServiceMapping]:
        """
        Attempt fuzzy matching for unknown services.
        
        Args:
            provider: Cloud provider
            service_name: Service name to match
            
        Returns:
            ServiceMapping if fuzzy match found, None otherwise
        """
        cache_key = f"{provider.value}:{service_name}"
        if cache_key in self._fuzzy_cache:
            return self._fuzzy_cache[cache_key]
        
        provider_mappings = self._base_mappings.get(provider, {})
        best_match = None
        best_score = 0.0
        
        # Simple fuzzy matching based on string similarity
        for known_service, mapping in provider_mappings.items():
            score = self._calculate_similarity(service_name, known_service)
            
            # Also check aliases
            for alias in mapping.aliases:
                alias_score = self._calculate_similarity(service_name, alias)
                score = max(score, alias_score)
            
            if score > best_score and score > 0.7:  # Threshold for fuzzy matching
                best_score = score
                best_match = mapping
        
        if best_match:
            fuzzy_mapping = ServiceMapping(
                provider_service_name=service_name,
                unified_category=best_match.unified_category,
                confidence=MappingConfidence.MEDIUM if best_score > 0.8 else MappingConfidence.LOW,
                description=f"Fuzzy match to {best_match.provider_service_name} (score: {best_score:.2f})",
                tags={'fuzzy_match': 'true', 'similarity_score': str(best_score)}
            )
            
            # Cache the result
            self._fuzzy_cache[cache_key] = fuzzy_mapping
            return fuzzy_mapping
        
        return None
    
    def _calculate_similarity(self, str1: str, str2: str) -> float:
        """
        Calculate similarity between two strings using Levenshtein distance.
        
        Args:
            str1: First string
            str2: Second string
            
        Returns:
            Similarity score between 0.0 and 1.0
        """
        # Simple implementation - could be enhanced with more sophisticated algorithms
        str1_lower = str1.lower()
        str2_lower = str2.lower()
        
        if str1_lower == str2_lower:
            return 1.0
        
        # Check if one string contains the other
        if str1_lower in str2_lower or str2_lower in str1_lower:
            return 0.8
        
        # Calculate Levenshtein distance
        len1, len2 = len(str1_lower), len(str2_lower)
        if len1 == 0:
            return 0.0 if len2 > 0 else 1.0
        if len2 == 0:
            return 0.0
        
        # Create distance matrix
        matrix = [[0] * (len2 + 1) for _ in range(len1 + 1)]
        
        # Initialize first row and column
        for i in range(len1 + 1):
            matrix[i][0] = i
        for j in range(len2 + 1):
            matrix[0][j] = j
        
        # Fill the matrix
        for i in range(1, len1 + 1):
            for j in range(1, len2 + 1):
                cost = 0 if str1_lower[i-1] == str2_lower[j-1] else 1
                matrix[i][j] = min(
                    matrix[i-1][j] + 1,      # deletion
                    matrix[i][j-1] + 1,      # insertion
                    matrix[i-1][j-1] + cost  # substitution
                )
        
        # Calculate similarity score
        max_len = max(len1, len2)
        distance = matrix[len1][len2]
        similarity = 1.0 - (distance / max_len)
        
        return max(0.0, similarity)
    
    def add_custom_rule(self, rule: CustomMappingRule):
        """
        Add a custom mapping rule for a client.
        
        Args:
            rule: Custom mapping rule to add
        """
        if rule.client_id not in self._custom_rules:
            self._custom_rules[rule.client_id] = []
        
        self._custom_rules[rule.client_id].append(rule)
        self.logger.info(f"Added custom rule for client {rule.client_id}: {rule.service_pattern} -> {rule.target_category.value}")
    
    def remove_custom_rule(self, client_id: str, rule_index: int) -> bool:
        """
        Remove a custom mapping rule for a client.
        
        Args:
            client_id: Client identifier
            rule_index: Index of rule to remove
            
        Returns:
            True if rule was removed, False otherwise
        """
        if client_id not in self._custom_rules:
            return False
        
        client_rules = self._custom_rules[client_id]
        if 0 <= rule_index < len(client_rules):
            removed_rule = client_rules.pop(rule_index)
            self.logger.info(f"Removed custom rule for client {client_id}: {removed_rule.service_pattern}")
            return True
        
        return False
    
    def get_custom_rules(self, client_id: str) -> List[CustomMappingRule]:
        """
        Get all custom mapping rules for a client.
        
        Args:
            client_id: Client identifier
            
        Returns:
            List of custom mapping rules
        """
        return self._custom_rules.get(client_id, [])
    
    def get_service_categories_for_provider(self, provider: CloudProvider) -> Dict[ServiceCategory, List[str]]:
        """
        Get all services grouped by category for a provider.
        
        Args:
            provider: Cloud provider
            
        Returns:
            Dictionary mapping categories to service lists
        """
        categories = {}
        provider_mappings = self._base_mappings.get(provider, {})
        
        for service_name, mapping in provider_mappings.items():
            category = mapping.unified_category
            if category not in categories:
                categories[category] = []
            categories[category].append(service_name)
        
        return categories
    
    def get_equivalent_services(
        self, 
        service_name: str, 
        source_provider: CloudProvider,
        target_providers: List[CloudProvider]
    ) -> Dict[CloudProvider, List[str]]:
        """
        Find equivalent services across providers.
        
        Args:
            service_name: Service name to find equivalents for
            source_provider: Provider of the source service
            target_providers: Providers to search for equivalents
            
        Returns:
            Dictionary mapping providers to equivalent service names
        """
        # Get the category of the source service
        source_mapping = self.map_service(source_provider, service_name)
        source_category = source_mapping.unified_category
        
        equivalents = {}
        
        for provider in target_providers:
            if provider == source_provider:
                continue
            
            provider_mappings = self._base_mappings.get(provider, {})
            equivalent_services = [
                service for service, mapping in provider_mappings.items()
                if mapping.unified_category == source_category
            ]
            
            if equivalent_services:
                equivalents[provider] = equivalent_services
        
        return equivalents
    
    def get_mapping_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about the service mappings.
        
        Returns:
            Dictionary with mapping statistics
        """
        stats = {
            'total_base_mappings': 0,
            'mappings_by_provider': {},
            'mappings_by_category': {},
            'custom_rules_by_client': {},
            'fuzzy_cache_size': len(self._fuzzy_cache)
        }
        
        # Count base mappings
        for provider, mappings in self._base_mappings.items():
            provider_count = len(mappings)
            stats['total_base_mappings'] += provider_count
            stats['mappings_by_provider'][provider.value] = provider_count
            
            # Count by category
            for mapping in mappings.values():
                category = mapping.unified_category.value
                if category not in stats['mappings_by_category']:
                    stats['mappings_by_category'][category] = 0
                stats['mappings_by_category'][category] += 1
        
        # Count custom rules
        for client_id, rules in self._custom_rules.items():
            stats['custom_rules_by_client'][client_id] = len(rules)
        
        return stats
    
    def validate_mapping_coverage(self, provider: CloudProvider, service_names: List[str]) -> Dict[str, Any]:
        """
        Validate mapping coverage for a list of services.
        
        Args:
            provider: Cloud provider
            service_names: List of service names to validate
            
        Returns:
            Dictionary with coverage analysis
        """
        coverage = {
            'total_services': len(service_names),
            'mapped_services': 0,
            'unmapped_services': [],
            'low_confidence_mappings': [],
            'coverage_percentage': 0.0
        }
        
        for service_name in service_names:
            mapping = self.map_service(provider, service_name)
            
            if mapping.unified_category != ServiceCategory.OTHER:
                coverage['mapped_services'] += 1
                
                if mapping.confidence in [MappingConfidence.LOW, MappingConfidence.UNKNOWN]:
                    coverage['low_confidence_mappings'].append({
                        'service_name': service_name,
                        'category': mapping.unified_category.value,
                        'confidence': mapping.confidence.value
                    })
            else:
                coverage['unmapped_services'].append(service_name)
        
        if coverage['total_services'] > 0:
            coverage['coverage_percentage'] = (coverage['mapped_services'] / coverage['total_services']) * 100
        
        return coverage
    
    def export_mappings(self, provider: Optional[CloudProvider] = None) -> Dict[str, Any]:
        """
        Export service mappings to a dictionary format.
        
        Args:
            provider: Optional provider to filter by
            
        Returns:
            Dictionary with exported mappings
        """
        export_data = {
            'export_timestamp': datetime.utcnow().isoformat(),
            'base_mappings': {},
            'custom_rules': {}
        }
        
        # Export base mappings
        providers_to_export = [provider] if provider else self._base_mappings.keys()
        
        for prov in providers_to_export:
            if prov in self._base_mappings:
                export_data['base_mappings'][prov.value] = {
                    service_name: mapping.to_dict()
                    for service_name, mapping in self._base_mappings[prov].items()
                }
        
        # Export custom rules
        for client_id, rules in self._custom_rules.items():
            filtered_rules = rules
            if provider:
                filtered_rules = [rule for rule in rules if rule.provider == provider]
            
            if filtered_rules:
                export_data['custom_rules'][client_id] = [
                    rule.to_dict() for rule in filtered_rules
                ]
        
        return export_data
    
    def import_mappings(self, import_data: Dict[str, Any]):
        """
        Import service mappings from a dictionary format.
        
        Args:
            import_data: Dictionary with mapping data to import
        """
        # Import base mappings
        if 'base_mappings' in import_data:
            for provider_str, mappings in import_data['base_mappings'].items():
                try:
                    provider = CloudProvider(provider_str)
                    if provider not in self._base_mappings:
                        self._base_mappings[provider] = {}
                    
                    for service_name, mapping_data in mappings.items():
                        mapping = ServiceMapping.from_dict(mapping_data)
                        self._base_mappings[provider][service_name] = mapping
                        
                except ValueError as e:
                    self.logger.warning(f"Invalid provider in import data: {provider_str}")
        
        # Import custom rules
        if 'custom_rules' in import_data:
            for client_id, rules_data in import_data['custom_rules'].items():
                if client_id not in self._custom_rules:
                    self._custom_rules[client_id] = []
                
                for rule_data in rules_data:
                    try:
                        rule = CustomMappingRule.from_dict(rule_data)
                        self._custom_rules[client_id].append(rule)
                    except (ValueError, KeyError) as e:
                        self.logger.warning(f"Invalid custom rule in import data: {e}")
        
        self.logger.info("Successfully imported service mappings")


# Global service mapper instance
service_mapper = ServiceMapper()


def get_unified_service_category(
    provider: CloudProvider, 
    service_name: str, 
    client_id: Optional[str] = None
) -> ServiceCategory:
    """
    Convenience function to get unified service category.
    
    Args:
        provider: Cloud provider
        service_name: Provider-specific service name
        client_id: Optional client ID for custom mappings
        
    Returns:
        Unified service category
    """
    mapping = service_mapper.map_service(provider, service_name, client_id)
    return mapping.unified_category


def add_custom_service_mapping(
    client_id: str,
    provider: CloudProvider,
    service_pattern: str,
    target_category: ServiceCategory,
    rule_type: str = "exact",
    priority: int = 100
):
    """
    Convenience function to add custom service mapping.
    
    Args:
        client_id: Client identifier
        provider: Cloud provider
        service_pattern: Service pattern to match
        target_category: Target unified category
        rule_type: Type of matching rule
        priority: Rule priority
    """
    rule = CustomMappingRule(
        client_id=client_id,
        provider=provider,
        service_pattern=service_pattern,
        target_category=target_category,
        rule_type=rule_type,
        priority=priority
    )
    
    service_mapper.add_custom_rule(rule)