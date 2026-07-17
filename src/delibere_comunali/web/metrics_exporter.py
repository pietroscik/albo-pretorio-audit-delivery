"""
Metrics Export Application for Dashboard Integration.

This module provides endpoints and utilities for exporting metrics
to be consumed by the dashboard and monitoring systems.
"""

import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List
import logging

from flask import Flask, jsonify, request
import redis

from ..utils.metrics_collector import get_metrics_collector
from ..utils.config import get_config


class MetricsExporter:
    """
    Metrics exporter for dashboard and monitoring integration.
    Provides both real-time metrics and historical data exports.
    """
    
    def __init__(self):
        self.redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
        self.metrics_collector = get_metrics_collector()
        self.config = get_config()
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
    
    def get_system_health(self) -> Dict[str, Any]:
        """
        Get overall system health metrics.
        
        Returns:
            Dictionary with system health information
        """
        try:
            # Check Redis connectivity
            redis_ping = self.redis_client.ping()
            redis_status = "connected" if redis_ping else "disconnected"
        except Exception:
            redis_status = "error"
        
        # Get worker status from metrics
        worker_status = self._get_worker_status()
        
        # Get queue sizes
        queue_sizes = self._get_queue_sizes()
        
        health_data = {
            "timestamp": datetime.now().isoformat(),
            "system_status": "operational",
            "redis_status": redis_status,
            "workers": worker_status,
            "queues": queue_sizes,
            "metrics_collector_status": "active"
        }
        
        return health_data
    
    def get_document_processing_metrics(self, days: int = 1) -> Dict[str, Any]:
        """
        Get document processing metrics for the specified number of days.
        
        Args:
            days: Number of days to include in the metrics
            
        Returns:
            Dictionary with document processing metrics
        """
        # Get local metrics summary
        summary = self.metrics_collector.get_local_metrics_summary(days)
        
        # Enhance with additional computed metrics
        if 'document_processing' in summary:
            dp_summary = summary['document_processing']
            
            # Calculate additional metrics
            total_processed = dp_summary['total_processed']
            avg_time = dp_summary['avg_processing_time']
            
            # Calculate throughput
            hours_in_period = days * 24
            throughput = total_processed / hours_in_period if hours_in_period > 0 else 0
            
            dp_summary['throughput_per_hour'] = throughput
            dp_summary['efficiency_score'] = self._calculate_efficiency_score(avg_time)
        
        return summary
    
    def get_error_metrics(self, days: int = 1) -> Dict[str, Any]:
        """
        Get error metrics for the specified number of days.
        
        Args:
            days: Number of days to include in the metrics
            
        Returns:
            Dictionary with error metrics
        """
        # Get local metrics summary
        summary = self.metrics_collector.get_local_metrics_summary(days)
        
        # Enhance with additional computed metrics
        if 'errors' in summary:
            error_summary = summary['errors']
            
            # Calculate error rates
            total_processed = self._get_total_processed_in_period(days)
            total_errors = error_summary['total_errors']
            
            error_rate = (total_errors / total_processed * 100) if total_processed > 0 else 0
            error_summary['error_rate_percent'] = error_rate
            error_summary['severity_score'] = self._calculate_severity_score(error_summary)
        
        return summary
    
    def export_metrics_to_file(self, output_path: Path, include_prometheus: bool = True) -> bool:
        """
        Export all metrics to a file for external consumption.
        
        Args:
            output_path: Path to output file
            include_prometheus: Whether to include Prometheus-formatted metrics
            
        Returns:
            True if successful, False otherwise
        """
        try:
            export_data = {
                "export_timestamp": datetime.now().isoformat(),
                "system_health": self.get_system_health(),
                "document_processing": self.get_document_processing_metrics(7),  # Last 7 days
                "errors": self.get_error_metrics(7)  # Last 7 days
            }
            
            if include_prometheus:
                try:
                    prometheus_metrics = self.metrics_collector.export_prometheus_metrics()
                    export_data["prometheus_metrics"] = prometheus_metrics
                except Exception as e:
                    self.logger.warning(f"Could not export Prometheus metrics: {e}")
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            return True
        except Exception as e:
            self.logger.error(f"Error exporting metrics to {output_path}: {e}")
            return False
    
    def _get_worker_status(self) -> Dict[str, Any]:
        """Get current worker status."""
        # This would typically query the actual worker status
        # For now, we'll return a placeholder based on metrics
        return {
            "ocr_workers": self._get_active_worker_count("ocr"),
            "standard_workers": self._get_active_worker_count("standard"),
            "audit_workers": self._get_active_worker_count("audit"),
            "total_active": self._get_total_active_workers()
        }
    
    def _get_queue_sizes(self) -> Dict[str, int]:
        """Get current queue sizes."""
        queue_names = ['ocr_queue', 'standard_queue', 'audit_queue']
        sizes = {}
        
        for queue_name in queue_names:
            try:
                # Try default queue first, then tenant-specific
                size_default = self.redis_client.llen(queue_name)
                sizes[queue_name] = size_default
            except Exception:
                sizes[queue_name] = 0
        
        return sizes
    
    def _get_active_worker_count(self, worker_type: str) -> int:
        """Get count of active workers of a specific type."""
        # Placeholder implementation - in a real system this would check actual worker status
        return 1  # Assuming at least one of each type is configured
    
    def _get_total_active_workers(self) -> int:
        """Get total count of active workers."""
        return 3  # Assuming 3 types of workers
    
    def _get_total_processed_in_period(self, days: int) -> int:
        """Get total documents processed in the specified period."""
        summary = self.metrics_collector.get_local_metrics_summary(days)
        return summary.get('document_processing', {}).get('total_processed', 0)
    
    def _calculate_efficiency_score(self, avg_processing_time: float) -> float:
        """Calculate efficiency score based on average processing time."""
        # Lower processing time = higher efficiency
        # Using inverse relationship with a maximum score of 100
        max_expected_time = 60.0  # seconds
        score = max(0, 100 * (1 - min(avg_processing_time / max_expected_time, 1)))
        return round(score, 2)
    
    def _calculate_severity_score(self, error_summary: Dict[str, Any]) -> float:
        """Calculate severity score based on error types and counts."""
        # Higher error rate = higher severity
        error_rate = error_summary.get('error_rate_percent', 0)
        severity = min(error_rate * 10, 100)  # Cap at 100
        return round(severity, 2)


# Flask app for metrics API
app = Flask(__name__)
metrics_exporter = MetricsExporter()


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    health_data = metrics_exporter.get_system_health()
    return jsonify(health_data)


@app.route('/metrics/documents', methods=['GET'])
def document_metrics():
    """Document processing metrics endpoint."""
    days = request.args.get('days', default=1, type=int)
    metrics = metrics_exporter.get_document_processing_metrics(days)
    return jsonify(metrics)


@app.route('/metrics/errors', methods=['GET'])
def error_metrics():
    """Error metrics endpoint."""
    days = request.args.get('days', default=1, type=int)
    metrics = metrics_exporter.get_error_metrics(days)
    return jsonify(metrics)


@app.route('/metrics/export', methods=['GET'])
def export_metrics():
    """Export metrics to file endpoint."""
    include_prometheus = request.args.get('prometheus', default=True, type=bool)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = Path("data") / f"metrics_export_{timestamp}.json"
    
    success = metrics_exporter.export_metrics_to_file(output_path, include_prometheus)
    
    if success:
        return jsonify({
            "status": "success",
            "file_path": str(output_path),
            "timestamp": datetime.now().isoformat()
        })
    else:
        return jsonify({"status": "error"}), 500


def main():
    """Run the metrics exporter API."""
    print("Starting Metrics Exporter API...")
    print("Available endpoints:")
    print("  GET /health - System health status")
    print("  GET /metrics/documents?days=N - Document processing metrics")
    print("  GET /metrics/errors?days=N - Error metrics")
    print("  GET /metrics/export - Export metrics to file")
    
    # Run Flask app
    app.run(host='0.0.0.0', port=8002, debug=False)


if __name__ == "__main__":
    main()