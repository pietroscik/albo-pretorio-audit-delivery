"""
Metrics Collection Module for Telemetry and Observability.

This module provides centralized metrics collection for the distributed system,
tracking business and system metrics for the RegTech framework.
"""

import time
import threading
from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import json
import logging
from pathlib import Path

from prometheus_client import Counter, Histogram, Gauge, start_http_server, CollectorRegistry
import redis


class MetricsCollector:
    """
    Centralized metrics collector for business and system metrics.
    Provides both Prometheus integration and local storage for offline analysis.
    """
    
    def __init__(self, redis_host: str = 'localhost', redis_port: int = 6379, prometheus_port: int = 8001):
        self.redis_client = redis.Redis(host=redis_host, port=redis_port, db=0, decode_responses=True)
        self.prometheus_port = prometheus_port
        self.local_metrics = defaultdict(deque)
        self.lock = threading.Lock()
        
        # Initialize Prometheus metrics
        self.registry = CollectorRegistry()
        
        # Business metrics
        self.documents_processed = Counter(
            'documents_processed_total',
            'Total documents processed',
            ['document_type', 'processing_method', 'ente'],
            registry=self.registry
        )
        
        self.processing_time = Histogram(
            'document_processing_seconds',
            'Time spent processing documents',
            ['document_type', 'processing_method', 'ente'],
            registry=self.registry
        )
        
        self.queue_size = Gauge(
            'redis_queue_size',
            'Current size of Redis queues',
            ['queue_name', 'ente'],
            registry=self.registry
        )
        
        # System metrics
        self.worker_status = Gauge(
            'worker_status',
            'Status of workers (1=active, 0=inactive)',
            ['worker_type', 'ente'],
            registry=self.registry
        )
        
        self.errors_count = Counter(
            'errors_total',
            'Total errors encountered',
            ['error_type', 'module', 'ente'],
            registry=self.registry
        )
        
        # Start Prometheus server
        try:
            start_http_server(self.prometheus_port, registry=self.registry)
            logging.info(f"Prometheus metrics server started on port {self.prometheus_port}")
        except Exception as e:
            logging.warning(f"Failed to start Prometheus server: {e}")
    
    def record_document_processed(self, document_type: str, processing_method: str, ente: str, processing_time_sec: float):
        """
        Record a document processing event.
        
        Args:
            document_type: Type of document ('native_pdf', 'scanned_pdf', etc.)
            processing_method: How it was processed ('standard', 'ocr', etc.)
            ente: Entity identifier
            processing_time_sec: Processing time in seconds
        """
        with self.lock:
            self.documents_processed.labels(
                document_type=document_type,
                processing_method=processing_method,
                ente=ente
            ).inc()
            
            self.processing_time.labels(
                document_type=document_type,
                processing_method=processing_method,
                ente=ente
            ).observe(processing_time_sec)
            
            # Store locally for offline analysis
            metric_entry = {
                'timestamp': datetime.now().isoformat(),
                'document_type': document_type,
                'processing_method': processing_method,
                'ente': ente,
                'processing_time_sec': processing_time_sec
            }
            self.local_metrics['document_processing'].append(metric_entry)
            
            # Keep only last 1000 entries to prevent memory overflow
            if len(self.local_metrics['document_processing']) > 1000:
                self.local_metrics['document_processing'].popleft()
    
    def record_error(self, error_type: str, module: str, ente: str, details: Optional[str] = None):
        """
        Record an error event.
        
        Args:
            error_type: Type of error (e.g., 'ocr_failure', 'parsing_error')
            module: Module where error occurred
            ente: Entity identifier
            details: Optional error details
        """
        with self.lock:
            self.errors_count.labels(
                error_type=error_type,
                module=module,
                ente=ente
            ).inc()
            
            # Store locally for offline analysis
            error_entry = {
                'timestamp': datetime.now().isoformat(),
                'error_type': error_type,
                'module': module,
                'ente': ente,
                'details': details
            }
            self.local_metrics['errors'].append(error_entry)
            
            # Keep only last 1000 entries to prevent memory overflow
            if len(self.local_metrics['errors']) > 1000:
                self.local_metrics['errors'].popleft()
    
    def update_queue_metrics(self, ente: str = 'default'):
        """
        Update Redis queue size metrics.
        
        Args:
            ente: Entity identifier for queue isolation
        """
        try:
            # Get sizes for all queues
            queue_names = ['ocr_queue', 'standard_queue', 'audit_queue']
            
            for queue_name in queue_names:
                # Use tenant-specific queue names
                tenant_queue_name = f"{queue_name}:{ente}" if ente != 'default' else queue_name
                queue_size = self.redis_client.llen(tenant_queue_name)
                
                self.queue_size.labels(
                    queue_name=queue_name,
                    ente=ente
                ).set(queue_size)
                
                # Store locally
                queue_entry = {
                    'timestamp': datetime.now().isoformat(),
                    'queue_name': queue_name,
                    'ente': ente,
                    'size': queue_size
                }
                self.local_metrics['queues'].append(queue_entry)
                
                # Keep only last 1000 entries to prevent memory overflow
                if len(self.local_metrics['queues']) > 1000:
                    self.local_metrics['queues'].popleft()
        except Exception as e:
            logging.error(f"Error updating queue metrics: {e}")
            self.record_error('queue_monitoring_error', 'metrics_collector', ente, str(e))
    
    def update_worker_status(self, worker_type: str, status: int, ente: str = 'default'):
        """
        Update worker status metrics.
        
        Args:
            worker_type: Type of worker ('ocr', 'standard', 'audit', etc.)
            status: Status (1 for active, 0 for inactive)
            ente: Entity identifier
        """
        self.worker_status.labels(
            worker_type=worker_type,
            ente=ente
        ).set(status)
        
        # Store locally
        worker_entry = {
            'timestamp': datetime.now().isoformat(),
            'worker_type': worker_type,
            'ente': ente,
            'status': status
        }
        self.local_metrics['workers'].append(worker_entry)
        
        # Keep only last 1000 entries to prevent memory overflow
        if len(self.local_metrics['workers']) > 1000:
            self.local_metrics['workers'].popleft()
    
    def get_local_metrics_summary(self, days: int = 1) -> Dict[str, Any]:
        """
        Get a summary of local metrics for the last N days.
        
        Args:
            days: Number of days to include in the summary
            
        Returns:
            Dictionary with metrics summary
        """
        cutoff_time = datetime.now() - timedelta(days=days)
        
        summary = {}
        
        for metric_type, entries in self.local_metrics.items():
            recent_entries = [
                entry for entry in entries 
                if datetime.fromisoformat(entry['timestamp']) >= cutoff_time
            ]
            
            if metric_type == 'document_processing':
                summary['document_processing'] = {
                    'total_processed': len(recent_entries),
                    'avg_processing_time': sum(e['processing_time_sec'] for e in recent_entries) / len(recent_entries) if recent_entries else 0,
                    'processing_methods': defaultdict(int),
                    'document_types': defaultdict(int)
                }
                
                for entry in recent_entries:
                    summary['document_processing']['processing_methods'][entry['processing_method']] += 1
                    summary['document_processing']['document_types'][entry['document_type']] += 1
            
            elif metric_type == 'errors':
                summary['errors'] = {
                    'total_errors': len(recent_entries),
                    'error_types': defaultdict(int),
                    'affected_modules': defaultdict(int)
                }
                
                for entry in recent_entries:
                    summary['errors']['error_types'][entry['error_type']] += 1
                    summary['errors']['affected_modules'][entry['module']] += 1
        
        return summary
    
    def export_metrics_to_json(self, output_path: Path):
        """
        Export all collected metrics to JSON file.
        
        Args:
            output_path: Path to output JSON file
        """
        export_data = {}
        
        for metric_type, entries in self.local_metrics.items():
            export_data[metric_type] = list(entries)
        
        export_data['export_timestamp'] = datetime.now().isoformat()
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
    
    def export_prometheus_metrics(self) -> str:
        """
        Export Prometheus-formatted metrics.
        
        Returns:
            String with Prometheus-formatted metrics
        """
        from prometheus_client import generate_latest
        return generate_latest(self.registry).decode('utf-8')


# Global metrics collector instance
_metrics_collector = None


def get_metrics_collector() -> MetricsCollector:
    """
    Get the global metrics collector instance.
    
    Returns:
        MetricsCollector instance
    """
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector


def main():
    """Test function for metrics collector."""
    import time
    
    collector = get_metrics_collector()
    
    print("Testing metrics collection...")
    
    # Simulate some metrics
    collector.record_document_processed('native_pdf', 'standard', 'test_ente', 2.5)
    collector.record_document_processed('scanned_pdf', 'ocr', 'test_ente', 15.2)
    collector.record_error('test_error', 'test_module', 'test_ente', 'Test error details')
    
    # Update queue metrics
    collector.update_queue_metrics('test_ente')
    
    # Update worker status
    collector.update_worker_status('ocr', 1, 'test_ente')
    
    print("Metrics recorded successfully")
    print("Local metrics summary:")
    summary = collector.get_local_metrics_summary()
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()