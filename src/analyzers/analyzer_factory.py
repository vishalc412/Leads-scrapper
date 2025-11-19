"""
Factory for creating AI analyzers based on model type.
"""

import logging
from typing import Optional

from .base_analyzer import BaseAnalyzer
from .anthropic_analyzer import AnthropicAnalyzer
from .openai_analyzer import OpenAIAnalyzer
from ..config import AIModel, get_config

logger = logging.getLogger(__name__)


class AnalyzerFactory:
    """Factory for creating appropriate analyzer based on model."""

    @staticmethod
    def create_analyzer(model: Optional[AIModel] = None) -> BaseAnalyzer:
        """
        Create an analyzer instance based on the model type.

        Args:
            model: AI model to use. If None, uses config default.

        Returns:
            Appropriate analyzer instance

        Raises:
            ValueError: If model type is not supported
        """
        if model is None:
            model = get_config().ai.model

        model_value = model.value if isinstance(model, AIModel) else model

        # Determine analyzer type based on model
        if "claude" in model_value.lower() or "anthropic" in model_value.lower():
            logger.info(f"Creating Anthropic analyzer for model: {model_value}")
            return AnthropicAnalyzer(model)

        elif "gpt" in model_value.lower() or "o1" in model_value.lower():
            logger.info(f"Creating OpenAI analyzer for model: {model_value}")
            return OpenAIAnalyzer(model)

        else:
            raise ValueError(
                f"Unsupported model: {model_value}. "
                f"Supported models: Anthropic Claude, OpenAI GPT"
            )

    @staticmethod
    def get_supported_models():
        """Get list of supported models."""
        return [model.value for model in AIModel]
