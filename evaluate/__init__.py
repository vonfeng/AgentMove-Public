"""Evaluation package for AgentMove.

This package contains evaluation utilities:
- analysis: Result analysis and summary generation
- evaluations: Prediction evaluation metrics (Accuracy, MRR, NDCG, etc.)
"""

from .evaluations import PredictionEvaluator

__all__ = [
    "PredictionEvaluator",
]

