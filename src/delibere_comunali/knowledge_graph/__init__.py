"""Knowledge Graph module for albo-pretorio-audit-delivery.

This module provides functionality for building, validating, and exporting
knowledge graphs from administrative data (Albo Pretorio).

Structure:
- models.py: Pydantic models for nodes, edges, and graph entities
- builder.py: Graph construction logic from CSV data
- exporters.py: Export functionality (GEXF, HTML, GraphML, RDF/Turtle)
"""