"""
Smart Model Selection - Auto-switch between Reasoning and Non-Reasoning

Automatically selects the best xAI model based on task type:
- Reasoning: For critical decisions requiring accuracy
- Non-Reasoning: For speed-critical tasks with simple logic

Same cost, different trade-offs: Speed vs Accuracy
"""

from enum import Enum
from typing import Optional


class TaskType(Enum):
    """Task types that determine model selection."""

    # Critical accuracy (use reasoning)
    CRISIS_DETECTION = "crisis_detection"
    CRISIS_VERIFICATION = "crisis_verification"
    EXIT_SIGNAL = "exit_signal"
    RED_FLAG_ANALYSIS = "red_flag_analysis"
    DEEP_COMPANY_ANALYSIS = "deep_company_analysis"
    EARNINGS_ANALYSIS = "earnings_analysis"
    REGULATORY_ANALYSIS = "regulatory_analysis"

    # Speed critical (use non-reasoning)
    MEME_SCANNING = "meme_scanning"
    QUICK_SENTIMENT = "quick_sentiment"
    BATCH_SENTIMENT = "batch_sentiment"
    SECTOR_ROTATION = "sector_rotation"
    VOLUME_CHECK = "volume_check"
    SIMPLE_CLASSIFICATION = "simple_classification"


class ModelSelector:
    """
    Intelligently selects between reasoning and non-reasoning models.

    Cost is the SAME ($0.20-0.50/M tokens), so we optimize for:
    - Reasoning: When accuracy is critical (money/safety at stake)
    - Non-Reasoning: When speed matters (simple checks, batch processing)
    """

    # Model names
    REASONING_MODEL = "grok-4-1-fast"  # Slower, more accurate
    NON_REASONING_MODEL = "grok-4-1-fast-non-reasoning"  # Faster, good accuracy

    # Tasks requiring reasoning (accuracy critical)
    REASONING_TASKS = {
        TaskType.CRISIS_DETECTION,
        TaskType.CRISIS_VERIFICATION,
        TaskType.EXIT_SIGNAL,
        TaskType.RED_FLAG_ANALYSIS,
        TaskType.DEEP_COMPANY_ANALYSIS,
        TaskType.EARNINGS_ANALYSIS,
        TaskType.REGULATORY_ANALYSIS,
    }

    @classmethod
    def select_model(cls, task_type: TaskType, force_reasoning: bool = False) -> str:
        """
        Select the optimal model for a task.

        Args:
            task_type: The type of task being performed
            force_reasoning: Force reasoning model regardless of task

        Returns:
            Model name string
        """
        if force_reasoning or task_type in cls.REASONING_TASKS:
            return cls.REASONING_MODEL
        else:
            return cls.NON_REASONING_MODEL

    @classmethod
    def get_task_type(cls, task_name: str) -> Optional[TaskType]:
        """
        Get TaskType from task name string.

        Args:
            task_name: Name of the task (e.g., "crisis_detection")

        Returns:
            TaskType enum or None
        """
        try:
            return TaskType(task_name)
        except ValueError:
            return None

    @classmethod
    def explain_choice(cls, task_type: TaskType) -> dict:
        """
        Explain why a particular model was chosen.

        Returns:
            Dict with model choice and reasoning
        """
        model = cls.select_model(task_type)
        is_reasoning = task_type in cls.REASONING_TASKS

        if is_reasoning:
            reason = "Critical accuracy needed - money/safety at stake"
            trade_off = "Slower (2-5s) but more accurate"
        else:
            reason = "Speed matters - simple check or batch processing"
            trade_off = "Faster (0.5-1s) with good accuracy"

        return {
            'task': task_type.value,
            'model': model,
            'reasoning': is_reasoning,
            'reason': reason,
            'trade_off': trade_off
        }


# Convenience functions for common use cases

def get_crisis_model() -> str:
    """Get model for crisis detection (reasoning)."""
    return ModelSelector.select_model(TaskType.CRISIS_DETECTION)


def get_exit_signal_model() -> str:
    """Get model for exit signals (reasoning)."""
    return ModelSelector.select_model(TaskType.EXIT_SIGNAL)


def get_meme_scan_model() -> str:
    """Get model for meme scanning (non-reasoning)."""
    return ModelSelector.select_model(TaskType.MEME_SCANNING)


def get_sentiment_model(quick: bool = True) -> str:
    """
    Get model for sentiment analysis.

    Args:
        quick: If True, use non-reasoning (fast). If False, use reasoning (deep).
    """
    task = TaskType.QUICK_SENTIMENT if quick else TaskType.DEEP_COMPANY_ANALYSIS
    return ModelSelector.select_model(task)


def get_sector_model() -> str:
    """Get model for sector rotation (non-reasoning)."""
    return ModelSelector.select_model(TaskType.SECTOR_ROTATION)


# Usage examples and guidelines
USAGE_GUIDE = """
MODEL SELECTION GUIDE
=====================

REASONING MODEL (grok-4-1-fast):
✓ Crisis detection/verification
✓ Exit signal analysis
✓ Red flag deep dives
✓ Earnings analysis
✓ Regulatory issues
✓ Any decision with $1K+ at stake

NON-REASONING MODEL (grok-4-1-fast-non-reasoning):
✓ Meme stock scanning (150 tickers)
✓ Quick sentiment checks
✓ Sector rotation (averaging)
✓ Batch processing
✓ Simple classification
✓ High-frequency monitoring

COST: Both models cost the SAME!
TRADE-OFF: Speed (0.5s) vs Accuracy (2s)

RULE OF THUMB:
- Money at risk? → Reasoning
- Speed matters? → Non-reasoning
- Not sure? → Reasoning (safer default)
"""
