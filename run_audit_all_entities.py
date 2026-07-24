#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script to run the complete audit pipeline for all three entities:

"""

import subprocess
import sys
from pathlib import Path

def run_audit_for_entity(ente):
    """
    Run the complete audit pipeline for a specific entity
    """
    print(f"\n{'='*60}")
    print(f"RUNNING AUDIT PIPELINE FOR: {ente}")
    print(f"{'='*60}")
    
    # Command to run the pipeline with all steps including audit
    cmd = [
        sys.executable, "-m", "delibere_comunali.cli.run_pipeline",
        "--ente", ente,
        "--base", f"./data/{ente}/albo_download"
    ]
    
    print(f"Executing command: {' '.join(cmd)}")
    
    # Run the pipeline
    result = subprocess.run(cmd)
    
    if result.returncode == 0:
        print(f"✅ Audit pipeline completed successfully for {ente}")
    else:
        print(f"❌ Audit pipeline failed for {ente} with return code: {result.returncode}")
    
    return result.returncode

def main():
    """
    Main function to run audit for all entities
    """
    entities = ['avella', 'baiano', 'quadrelle']
    
    print("Starting audit pipeline for all entities...")
    print(f"Entities to process: {', '.join(entities)}")
    
    all_success = True
    
    for entity in entities:
        return_code = run_audit_for_entity(entity)
        if return_code != 0:
            all_success = False
    
    print(f"\n{'='*60}")
    if all_success:
        print("🎉 ALL ENTITIES PROCESSED SUCCESSFULLY!")
        print("Audit reports should be available in:")
        for entity in entities:
            print(f"  - data/{entity}/albo_download/report/")
        print("Consolidated reports should be available in: data/albo_download/report/")
    else:
        print("⚠️  Some entities failed during processing.")
    print(f"{'='*60}")
    
    return 0 if all_success else 1

if __name__ == "__main__":
    sys.exit(main())