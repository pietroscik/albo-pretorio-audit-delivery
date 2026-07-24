import asyncio
from src.audit_processor import AuditProcessor
from src.config import Config
import os
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def main():
    # Create main data directory
    os.makedirs(Config.DATA_DIR, exist_ok=True)
    
    # List of entities to process
    entities = ['avella', 'baiano', 'quadrelle']
    
    # Process each entity
    for entity in entities:
        logging.info(f"Processing entity: {entity}")
        
        # Update config for current entity
        Config.ENTITY_NAME = entity
        Config.BASE_URL = f"https://albopretorio.comune.{entity}.av.it"
        
        # Create entity-specific directories
        entity_data_dir = Path(Config.DATA_DIR) / entity
        os.makedirs(entity_data_dir, exist_ok=True)
        
        # Create report directory for this entity
        entity_report_dir = entity_data_dir / 'albo_download' / 'report'
        os.makedirs(entity_report_dir, exist_ok=True)
        
        # Initialize processor for this entity
        processor = AuditProcessor(config=Config)
        
        # Run full audit process for this entity
        await processor.run_full_audit()
        
        # Generate all required reports for this entity
        logging.info(f"Generating reports for {entity}")
        
        # 1. Main report
        report_content = await processor.generate_detailed_report()
        report_file = entity_report_dir / 'report.md'
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report_content)
        logging.info(f"Generated report for {entity}: {report_file}")
        
        # 2. Filtered files report
        filtered_report = await processor.generate_filtered_files_report()
        filtered_file = entity_report_dir / 'filtered_files_report.md'
        with open(filtered_file, 'w', encoding='utf-8') as f:
            f.write(filtered_report)
        logging.info(f"Generated filtered files report for {entity}: {filtered_file}")
        
        # 3. Procedural analysis report
        procedural_report = await processor.generate_procedural_analysis_report()
        procedural_file = entity_report_dir / 'procedural_analysis_report.md'
        with open(procedural_file, 'w', encoding='utf-8') as f:
            f.write(procedural_report)
        logging.info(f"Generated procedural analysis report for {entity}: {procedural_file}")
        
        # 4. Antifrode alerts (these go to main report directory as well)
        antifrode_alerts = await processor.generate_antifrode_alerts()
        antifrode_file_main = Path('data/albo_download/report') / 'alert_antifrode.md'
        os.makedirs(antifrode_file_main.parent, exist_ok=True)
        with open(antifrode_file_main, 'w', encoding='utf-8') as f:
            f.write(antifrode_alerts)
        logging.info(f"Generated antifrode alerts: {antifrode_file_main}")
        
        # Also create entity-specific antifrode alerts
        antifrode_file_entity = entity_report_dir / 'alert_antifrode.md'
        with open(antifrode_file_entity, 'w', encoding='utf-8') as f:
            f.write(antifrode_alerts)
        logging.info(f"Generated entity-specific antifrode alerts for {entity}: {antifrode_file_entity}")
        
        # 5. Knowledge graph (already handled by processor, but ensure it's in entity dir too)
        # Copy knowledge graph to entity directory if it exists in main
        main_kg = Path('data/albo_download/report/knowledge_graph.gexf')
        entity_kg = entity_report_dir / 'knowledge_graph.gexf'
        if main_kg.exists():
            import shutil
            shutil.copy2(main_kg, entity_kg)
            logging.info(f"Copied knowledge graph to entity directory: {entity_kg}")
    
    logging.info("All entities processed successfully")

if __name__ == "__main__":
    asyncio.run(main())