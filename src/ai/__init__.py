"""
AI Intelligence Layer

DeepSeek integration, AI-assisted learning, and ecosystem generation.
"""

from src.ai.deepseek_intelligence import (
    DeepSeekIntelligence,
    get_deepseek_intelligence,
)

# Alias for backward compatibility
get_deepseek = get_deepseek_intelligence

__all__ = [
    'DeepSeekIntelligence',
    'get_deepseek',
    'get_deepseek_intelligence',
]
