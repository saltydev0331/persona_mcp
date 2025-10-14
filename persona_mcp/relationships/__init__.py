"""
Relationship management system for persona interactions.

This module provides relationship tracking, compatibility scoring, and 
emotional state management for personas.
"""

from .manager import RelationshipManager
from .compatibility import CompatibilityEngine

__all__ = ['RelationshipManager', 'CompatibilityEngine']