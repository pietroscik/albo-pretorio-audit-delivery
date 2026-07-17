"""
Components package for the web dashboard.
Contains reusable UI components for data visualization.
"""

from .financial_metrics import render_financial_metrics, calculate_financial_summary
from .tabular_view import render_tabular_view, filter_events_by_criteria
from .knowledge_graph import render_knowledge_graph, extract_entities_for_graph, render_entity_statistics

__all__ = [
    'render_financial_metrics',
    'calculate_financial_summary',
    'render_tabular_view', 
    'filter_events_by_criteria',
    'render_knowledge_graph',
    'extract_entities_for_graph',
    'render_entity_statistics'
]