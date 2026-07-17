"""
Orchestrator module for the Albo Pretorio Audit system.
Coordinates the execution of various analysis modules and manages data flow.
"""

import os
import sys
import time
import json
from pathlib import Path
from typing import Dict, List, Optional
import logging
import subprocess

from ..utils.logger import get_logger
from ..utils.config import get_config
from ..utils.metrics_collector import get_metrics_collector
from ..utils.privacy_guard import get_privacy_guard

logger = get_logger(__name__)
metrics_collector = get_metrics_collector()
privacy_guard = get_privacy_guard()


class CentralOrchestrator:
    """
    Central orchestrator for coordinating the execution of various analysis modules.
    Implements the enterprise workflow patterns and manages cross-module data contracts.
    """
    
    def __init__(self, config_manager=None):
        self.config_manager = config_manager or get_config()
        self.modules = {}
        self.execution_history = []
    
    def execute_full_workflow(self, ente: str):
        """
        Execute the complete enterprise workflow for a given entity.
        
        Args:
            ente: Name of the entity to analyze
        """
        start_time = time.time()
        logger.info(f"Starting full workflow for entity: {ente}")
        
        try:
            # Apply privacy compliance measures before processing
            self._ensure_privacy_compliance(ente)
            
            # Update worker status for monitoring
            metrics_collector.update_worker_status('orchestrator', 1, ente)
            
            # Execute scraping phase
            self._execute_phase("scraping", ente)
            
            # Execute analysis phase
            self._execute_phase("analysis", ente)
            
            # Execute risk assessment phase
            self._execute_phase("risk_assessment", ente)
            
            # Execute audit phase
            self._execute_phase("audit", ente)
            
            # Execute RAG phase
            self._execute_phase("rag", ente)
            
            # Update queue metrics during execution
            metrics_collector.update_queue_metrics(ente)
            
            # Apply privacy compliance measures after processing
            self._apply_privacy_measures(ente)
            
            total_time = time.time() - start_time
            logger.info(f"Full workflow completed for {ente} in {total_time:.2f} seconds")
            
            # Record metrics for the full workflow
            metrics_collector.record_document_processed(
                document_type='workflow_execution',
                processing_method='full',
                ente=ente,
                processing_time_sec=total_time
            )
            
        except Exception as e:
            logger.error(f"Error in full workflow for {ente}: {e}")
            
            # Record error metrics
            metrics_collector.record_error(
                error_type='workflow_error',
                module='orchestrator',
                ente=ente,
                details=str(e)
            )
            
            raise
        finally:
            # Update worker status
            metrics_collector.update_worker_status('orchestrator', 0, ente)
    
    def execute_analysis_only(self, ente: str):
        """
        Execute only the analysis phase for a given entity.
        
        Args:
            ente: Name of the entity to analyze
        """
        start_time = time.time()
        logger.info(f"Starting analysis-only workflow for entity: {ente}")
        
        try:
            # Apply privacy compliance measures before processing
            self._ensure_privacy_compliance(ente)
            
            # Update worker status for monitoring
            metrics_collector.update_worker_status('orchestrator', 1, ente)
            
            # Execute analysis phase only
            self._execute_phase("analysis", ente)
            
            # Update queue metrics during execution
            metrics_collector.update_queue_metrics(ente)
            
            # Apply privacy compliance measures after processing
            self._apply_privacy_measures(ente)
            
            total_time = time.time() - start_time
            logger.info(f"Analysis-only workflow completed for {ente} in {total_time:.2f} seconds")
            
            # Record metrics for the analysis workflow
            metrics_collector.record_document_processed(
                document_type='workflow_execution',
                processing_method='analysis_only',
                ente=ente,
                processing_time_sec=total_time
            )
            
        except Exception as e:
            logger.error(f"Error in analysis-only workflow for {ente}: {e}")
            
            # Record error metrics
            metrics_collector.record_error(
                error_type='analysis_workflow_error',
                module='orchestrator',
                ente=ente,
                details=str(e)
            )
            
            raise
        finally:
            # Update worker status
            metrics_collector.update_worker_status('orchestrator', 0, ente)
    
    def execute_scraping_only(self, ente: str):
        """
        Execute only the scraping phase for a given entity.
        
        Args:
            ente: Name of the entity to analyze
        """
        start_time = time.time()
        logger.info(f"Starting scraping-only workflow for entity: {ente}")
        
        try:
            # Apply privacy compliance measures before processing
            self._ensure_privacy_compliance(ente)
            
            # Update worker status for monitoring
            metrics_collector.update_worker_status('orchestrator', 1, ente)
            
            # Execute scraping phase only
            self._execute_phase("scraping", ente)
            
            # Update queue metrics during execution
            metrics_collector.update_queue_metrics(ente)
            
            # Apply privacy compliance measures after processing
            self._apply_privacy_measures(ente)
            
            total_time = time.time() - start_time
            logger.info(f"Scraping-only workflow completed for {ente} in {total_time:.2f} seconds")
            
            # Record metrics for the scraping workflow
            metrics_collector.record_document_processed(
                document_type='workflow_execution',
                processing_method='scraping_only',
                ente=ente,
                processing_time_sec=total_time
            )
            
        except Exception as e:
            logger.error(f"Error in scraping-only workflow for {ente}: {e}")
            
            # Record error metrics
            metrics_collector.record_error(
                error_type='scraping_workflow_error',
                module='orchestrator',
                ente=ente,
                details=str(e)
            )
            
            raise
        finally:
            # Update worker status
            metrics_collector.update_worker_status('orchestrator', 0, ente)
    
    def _execute_phase(self, phase: str, ente: str):
        """
        Execute a specific phase of the workflow.
        
        Args:
            phase: Name of the phase to execute
            ente: Name of the entity to analyze
        """
        phase_start_time = time.time()
        logger.info(f"Executing {phase} phase for entity: {ente}")
        
        try:
            if phase == "scraping":
                self._run_scraping(ente)
            elif phase == "analysis":
                self._run_analysis(ente)
            elif phase == "risk_assessment":
                self._run_risk_assessment(ente)
            elif phase == "audit":
                self._run_audit(ente)
            elif phase == "rag":
                self._run_rag(ente)
            else:
                raise ValueError(f"Unknown phase: {phase}")
            
            phase_time = time.time() - phase_start_time
            logger.info(f"{phase} phase completed for {ente} in {phase_time:.2f} seconds")
            
            # Record metrics for the phase
            metrics_collector.record_document_processed(
                document_type='phase_execution',
                processing_method=phase,
                ente=ente,
                processing_time_sec=phase_time
            )
            
        except Exception as e:
            logger.error(f"Error in {phase} phase for {ente}: {e}")
            
            # Record error metrics
            metrics_collector.record_error(
                error_type=f'{phase}_error',
                module='orchestrator',
                ente=ente,
                details=str(e)
            )
            
            raise
    
    def _run_scraping(self, ente: str):
        """Run the scraping phase."""
        from ..scraping.new_albo_scraper import scrape_albo_comune
        
        try:
            scrape_albo_comune(ente)
        except Exception as e:
            logger.error(f"Scraping failed for {ente}: {e}")
            raise
    
    def _run_analysis(self, ente: str):
        """Run the analysis phase."""
        # Execute the analysis module
        cmd = [
            sys.executable, 
            "-c",
            f"""
import sys
sys.path.insert(0, '.')
from delibere_comunali.parsing.analyze_albo import main
import argparse

# Simulate command line arguments
class Args:
    pass

args = Args()
args.ente = "{ente}"

# Execute the main function
main(args)
"""
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"Analysis failed for {ente}: {result.stderr}")
            raise RuntimeError(f"Analysis failed: {result.stderr}")
    
    def _run_risk_assessment(self, ente: str):
        """Run the risk assessment phase."""
        cmd = [
            sys.executable,
            "-c",
            f"""
import sys
sys.path.insert(0, '.')
from delibere_comunali.analysis.risk_assessment import main
import argparse

class Args:
    pass

args = Args()
args.ente = "{ente}"

main(args)
"""
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"Risk assessment failed for {ente}: {result.stderr}")
            raise RuntimeError(f"Risk assessment failed: {result.stderr}")
    
    def _run_audit(self, ente: str):
        """Run the audit phase."""
        cmd = [
            sys.executable,
            "-c",
            f"""
import sys
sys.path.insert(0, '.')
from delibere_comunali.processing.audit_engine import main
import argparse

class Args:
    pass

args = Args()
args.ente = "{ente}"

main(args)
"""
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"Audit failed for {e}: {result.stderr}")
            raise RuntimeError(f"Audit failed: {result.stderr}")
    
    def _run_rag(self, ente: str):
        """Run the RAG phase."""
        cmd = [
            sys.executable,
            "-c",
            f"""
import sys
sys.path.insert(0, '.')
from delibere_comunali.rag.rag_app import main
import argparse

class Args:
    pass

args = Args()
args.ente = "{ente}"

main(args)
"""
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"RAG failed for {ente}: {result.stderr}")
            raise RuntimeError(f"RAG failed: {result.stderr}")
    
    def _ensure_privacy_compliance(self, ente: str):
        """Ensure privacy compliance before processing."""
        logger.info(f"Ensuring privacy compliance for entity: {ente}")
        
        # Verify data protection measures are in place
        data_path = Path(self.config_manager.paths.data_dir) / ente
        if data_path.exists():
            # Apply retention policy check
            privacy_guard.apply_retention_policy(data_path)
        
        # Record privacy compliance check
        metrics_collector.record_document_processed(
            document_type='privacy_check',
            processing_method='gdpr_compliance',
            ente=ente,
            processing_time_sec=0.1  # Minimal time for check
        )
    
    def _apply_privacy_measures(self, ente: str):
        """Apply privacy measures after processing."""
        logger.info(f"Applying privacy measures for entity: {ente}")
        
        # Generate privacy compliance report
        entities = [ente]
        privacy_report = privacy_guard.generate_privacy_report(entities)
        
        # Save privacy report
        report_path = Path(self.config_manager.paths.data_dir) / ente / "reports" / "privacy_compliance.json"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(privacy_report, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Privacy compliance report saved to: {report_path}")
        
        # Record privacy measures applied
        metrics_collector.record_document_processed(
            document_type='privacy_measures',
            processing_method='data_protection',
            ente=ente,
            processing_time_sec=0.2  # Time for report generation
        )