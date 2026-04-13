"""duecare.publishing - HF Hub, Kaggle, reports, model cards."""

from .hf_hub import hf_hub as _hf_hub  # noqa: F401
from .kaggle import kaggle as _kaggle  # noqa: F401
from .reports import reports as _reports  # noqa: F401
from .model_card import model_card as _model_card  # noqa: F401

from .hf_hub.hf_hub import HFHubPublisher, is_hf_hub_available
from .kaggle.kaggle import KagglePublisher, is_kaggle_cli_available
from .reports.reports import MarkdownReportGenerator
from .model_card.model_card import ModelCardGenerator

__all__ = [
    "HFHubPublisher",
    "is_hf_hub_available",
    "KagglePublisher",
    "is_kaggle_cli_available",
    "MarkdownReportGenerator",
    "ModelCardGenerator",
]
