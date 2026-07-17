#!/usr/bin/env python3
"""
End-to-End Simulation Script for Load Balancing between Standard Engine and OCR Workers.

This script simulates a realistic ingestion scenario with mixed PDF types
(native text and scanned) to test the load distribution between the main
audit engine and OCR workers via Redis queue.
"""

import asyncio
import os
import sys
import random
import time
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any
import logging

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import redis
import pandas as pd
from faker import Faker

from src.delibere_comunali.parsing.ocr_processor import is_pdf_scanned, extract_text_from_scanned_pdf
from src.delibere_comunali.parsing.text_extractor import TextExtractor
from src.delibere_comunali.utils.config import get_config
from src.delibere_comunali.utils.logger import get_logger

logger = get_logger(__name__)
fake = Faker('it_IT')


class MockPDFGenerator:
    """Generate mock PDF files for testing."""
    
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(exist_ok=True)
    
    def create_mock_native_pdf(self, filename: str, content: str = None) -> Path:
        """Create a mock PDF with native text."""
        import io
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        
        if content is None:
            content = fake.paragraph(nb_sentences=20)
        
        pdf_path = self.output_dir / filename
        
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)
        c.drawString(100, 750, "Documento Comunale")
        y = 700
        for line in content.split('\n'):
            if y < 50:
                c.showPage()
                y = 750
            c.drawString(100, y, line[:80])  # Limit line length
            y -= 20
        c.save()
        
        with open(pdf_path, 'wb') as f:
            f.write(buffer.getvalue())
        
        return pdf_path
    
    def create_mock_scanned_pdf(self, filename: str, content: str = None) -> Path:
        """Create a mock "scanned" PDF by converting to image and back to PDF."""
        import io
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        from PIL import Image
        import fitz  # PyMuPDF
        
        if content is None:
            content = fake.paragraph(nb_sentences=20)
        
        # First create a text-based PDF
        temp_pdf_path = self.output_dir / f"temp_{filename}"
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)
        c.drawString(100, 750, "Documento Comunale Scansionato")
        y = 700
        for line in content.split('\n'):
            if y < 50:
                c.showPage()
                y = 750
            c.drawString(100, y, line[:80])
            y -= 20
        c.save()
        
        with open(temp_pdf_path, 'wb') as f:
            f.write(buffer.getvalue())
        
        # Convert to image and back to PDF to simulate scan
        output_path = self.output_dir / filename
        doc = fitz.open(temp_pdf_path)
        img_bytes = []
        
        for page in doc:
            pix = page.get_pixmap(matrix=fitz.Matrix(150/72, 150/72))  # Lower res to simulate scan
            img_data = pix.tobytes("png")
            img_bytes.append(img_data)
        
        doc.close()
        os.remove(temp_pdf_path)  # Remove temp file
        
        # Create a new PDF from images
        doc_out = fitz.open()
        for img_data in img_bytes:
            img_stream = io.BytesIO(img_data)
            img = Image.open(img_stream)
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='PNG')
            img_byte_arr = img_byte_arr.getvalue()
            
            page = doc_out.new_page()
            page.insert_image(page.rect, stream=img_byte_arr)
        
        doc_out.save(str(output_path))
        doc_out.close()
        
        return output_path


class LoadBalancerSimulator:
    """Simulate load balancing between standard engine and OCR workers."""
    
    def __init__(self, data_dir: Path, redis_host: str = 'localhost', redis_port: int = 6379):
        self.data_dir = data_dir
        self.redis_client = redis.Redis(host=redis_host, port=redis_port, db=0, decode_responses=True)
        self.text_extractor = TextExtractor(get_config())
        self.results = {
            'native_processed': 0,
            'ocr_processed': 0,
            'queue_timeouts': 0,
            'processing_times': [],
            'error_count': 0
        }
    
    async def simulate_ingestion(self, pdf_paths: List[Path], concurrency: int = 3) -> Dict[str, Any]:
        """Simulate ingestion of mixed PDF types with concurrent processing."""
        semaphore = asyncio.Semaphore(concurrency)
        
        async def process_pdf(pdf_path: Path):
            async with semaphore:
                start_time = time.time()
                try:
                    # Determine if PDF is scanned
                    is_scanned = await self._is_pdf_scanned_async(pdf_path)
                    
                    if is_scanned:
                        # Route to OCR worker via Redis queue
                        result = await self._process_via_ocr_worker(pdf_path)
                        self.results['ocr_processed'] += 1
                        logger.info(f"Processed via OCR: {pdf_path.name}")
                    else:
                        # Process via standard engine
                        result = await self._process_via_standard_engine(pdf_path)
                        self.results['native_processed'] += 1
                        logger.info(f"Processed via standard engine: {pdf_path.name}")
                    
                    processing_time = time.time() - start_time
                    self.results['processing_times'].append(processing_time)
                    
                    return result
                except Exception as e:
                    self.results['error_count'] += 1
                    logger.error(f"Error processing {pdf_path.name}: {e}")
                    return None
        
        tasks = [process_pdf(pdf_path) for pdf_path in pdf_paths]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return self.results
    
    async def _is_pdf_scanned_async(self, pdf_path: Path) -> bool:
        """Async wrapper for PDF scanning detection."""
        # In real scenario, this would be truly async
        # For now, we'll simulate with a sync call
        try:
            return is_pdf_scanned(pdf_path)
        except:
            # If OCR dependencies aren't available, assume it's native text
            return False
    
    async def _process_via_ocr_worker(self, pdf_path: Path) -> Dict[str, Any]:
        """Simulate processing via OCR worker through Redis queue."""
        # Simulate queueing to Redis
        queue_item = {
            'task_id': f"ocr_task_{pdf_path.stem}_{int(time.time())}",
            'pdf_path': str(pdf_path),
            'status': 'queued',
            'created_at': datetime.now().isoformat(),
            'estimated_duration': random.uniform(10, 60)  # 10-60 seconds
        }
        
        # Add to Redis queue
        self.redis_client.lpush('ocr_queue', str(queue_item))
        
        # Simulate worker processing time
        processing_delay = random.uniform(5, 30)  # Variable processing time
        await asyncio.sleep(processing_delay)
        
        # Simulate OCR processing result
        try:
            text = extract_text_from_scanned_pdf(pdf_path)
            result = {
                'task_id': queue_item['task_id'],
                'status': 'completed',
                'text_length': len(text),
                'processing_time': processing_delay,
                'quality_score': random.uniform(0.6, 1.0)  # Simulated OCR quality
            }
            
            # Mark as processed in Redis
            self.redis_client.set(f"ocr_result:{queue_item['task_id']}", str(result))
            self.redis_client.lrem('ocr_queue', 1, str(queue_item))
            
            return result
        except Exception as e:
            error_result = {
                'task_id': queue_item['task_id'],
                'status': 'failed',
                'error': str(e),
                'processing_time': processing_delay
            }
            self.redis_client.set(f"ocr_result:{queue_item['task_id']}", str(error_result))
            return error_result
    
    async def _process_via_standard_engine(self, pdf_path: Path) -> Dict[str, Any]:
        """Simulate processing via standard engine."""
        # Simulate processing delay
        processing_delay = random.uniform(1, 5)  # Faster for native text
        await asyncio.sleep(processing_delay)
        
        try:
            # Use the text extractor
            text, source = self.text_extractor.extract(pdf_path)
            result = {
                'pdf_path': str(pdf_path),
                'status': 'completed',
                'text_length': len(text),
                'source': source,
                'processing_time': processing_delay
            }
            return result
        except Exception as e:
            return {
                'pdf_path': str(pdf_path),
                'status': 'failed',
                'error': str(e),
                'processing_time': processing_delay
            }


async def main():
    """Main simulation function."""
    print("🧪 Starting End-to-End Load Balancing Simulation...")
    
    # Setup
    temp_dir = Path(tempfile.mkdtemp(prefix="e2e_simulation_"))
    mock_generator = MockPDFGenerator(temp_dir / "mock_pdfs")
    
    try:
        # Generate test data
        print("📚 Generating mock PDF documents...")
        native_pdfs = []
        scanned_pdfs = []
        
        # Create 10 native text PDFs
        for i in range(10):
            content = fake.paragraph(nb_sentences=random.randint(10, 30))
            pdf_path = mock_generator.create_mock_native_pdf(f"native_{i:02d}.pdf", content)
            native_pdfs.append(pdf_path)
        
        # Create 5 scanned PDFs
        for i in range(5):
            content = fake.paragraph(nb_sentences=random.randint(15, 25))
            pdf_path = mock_generator.create_mock_scanned_pdf(f"scanned_{i:02d}.pdf", content)
            scanned_pdfs.append(pdf_path)
        
        all_pdfs = native_pdfs + scanned_pdfs
        print(f"✅ Generated {len(native_pdfs)} native and {len(scanned_pdfs)} scanned PDFs")
        
        # Run simulation
        print("🔄 Running load balancing simulation...")
        simulator = LoadBalancerSimulator(temp_dir)
        results = await simulator.simulate_ingestion(all_pdfs, concurrency=3)
        
        # Print results
        print("\n📊 Simulation Results:")
        print(f"  Native text PDFs processed: {results['native_processed']}")
        print(f"  Scanned PDFs processed via OCR: {results['ocr_processed']}")
        print(f"  Total errors: {results['error_count']}")
        print(f"  Queue timeouts: {results['queue_times']}")
        
        if results['processing_times']:
            avg_time = sum(results['processing_times']) / len(results['processing_times'])
            print(f"  Average processing time: {avg_time:.2f}s")
            print(f"  Min processing time: {min(results['processing_times']):.2f}s")
            print(f"  Max processing time: {max(results['processing_times']):.2f}s")
        
        print("\n✅ End-to-End Simulation Completed Successfully!")
        
        # Generate summary report
        report_data = {
            'simulation_timestamp': datetime.now().isoformat(),
            'total_documents': len(all_pdfs),
            'native_processed': results['native_processed'],
            'ocr_processed': results['ocr_processed'],
            'error_rate': results['error_count'] / len(all_pdfs) if all_pdfs else 0,
            'average_processing_time': sum(results['processing_times']) / len(results['processing_times']) if results['processing_times'] else 0
        }
        
        report_df = pd.DataFrame([report_data])
        report_path = temp_dir / "simulation_report.csv"
        report_df.to_csv(report_path, index=False)
        print(f"📋 Report saved to: {report_path}")
        
    except Exception as e:
        print(f"❌ Simulation failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Cleanup
        print(f"\n🧹 Cleaning up temporary directory: {temp_dir}")
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run the simulation
    asyncio.run(main())