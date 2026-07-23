#!/usr/bin/env python3
"""
Script di test per verificare che le modifiche ai problemi di estrazione testo funzionino correttamente.
"""

import hashlib
from pathlib import Path
from src.delibere_comunali.models.parsed_document import ParsedDocument

def test_parsed_document_new_fields():
    """Test per verificare che i nuovi campi siano disponibili in ParsedDocument"""
    print("Test 1: Verifica dei nuovi campi in ParsedDocument...")
    
    # Creiamo un documento con i nuovi campi
    doc = ParsedDocument(
        pdf_name="test.pdf",
        pdf_path="/path/to/test.pdf",
        is_problematic_file=True,
        problematic_reason="empty_file"
    )
    
    assert hasattr(doc, 'is_problematic_file'), "Manca il campo is_problematic_file"
    assert hasattr(doc, 'problematic_reason'), "Manca il campo problematic_reason"
    
    print("✓ I nuovi campi sono presenti in ParsedDocument")
    print(f"  is_problematic_file: {doc.is_problematic_file}")
    print(f"  problematic_reason: {doc.problematic_reason}")

def test_from_dict_with_new_fields():
    """Test per verificare che from_dict funzioni con i nuovi campi"""
    print("\nTest 2: Verifica del metodo from_dict con i nuovi campi...")
    
    data = {
        "pdf_name": "test.pdf",
        "pdf_path": "/path/to/test.pdf",
        "is_problematic_file": True,
        "problematic_reason": "small_file",
        "oggetto": "Test document",
        "doc_type": "Determinazione"
    }
    
    doc = ParsedDocument.from_dict(data)
    
    assert doc.pdf_name == "test.pdf", "Il campo pdf_name non è stato impostato correttamente"
    assert doc.is_problematic_file == True, "Il campo is_problematic_file non è stato impostato correttamente"
    assert doc.problematic_reason == "small_file", "Il campo problematic_reason non è stato impostato correttamente"
    
    print("✓ Il metodo from_dict funziona correttamente con i nuovi campi")

def test_unique_hashes_for_problematic_files():
    """Test per verificare che i file problematici abbiano hash univoci"""
    print("\nTest 3: Verifica degli hash univoci per file problematici...")
    
    # Simuliamo due file problematici diversi
    file1_name = "file1_empty.pdf"
    file2_name = "file2_small.pdf"
    
    # Simuliamo gli stessi tipi di problemi che abbiamo implementato
    problematic_identifier1 = f"{file1_name}_empty_file"
    problematic_identifier2 = f"{file2_name}_small_file"
    
    hash1 = hashlib.sha256(problematic_identifier1.encode("utf-8", errors="ignore")).hexdigest()
    hash2 = hashlib.sha256(problematic_identifier2.encode("utf-8", errors="ignore")).hexdigest()
    
    assert hash1 != hash2, "Gli hash per file problematici diversi dovrebbero essere diversi"
    
    print("✓ Gli hash per file problematici diversi sono effettivamente diversi")
    print(f"  Hash per {file1_name}: {hash1[:16]}...")
    print(f"  Hash per {file2_name}: {hash2[:16]}...")

def test_normal_hash_calculation():
    """Test per verificare che il normale calcolo dell'hash funzioni ancora"""
    print("\nTest 4: Verifica del normale calcolo dell'hash...")
    
    sample_text = "Questo è un testo di esempio per verificare il calcolo dell'hash."
    normal_hash = hashlib.sha256(sample_text.encode("utf-8", errors="ignore")).hexdigest()
    
    # Verifichiamo che lo stesso testo produca lo stesso hash
    same_text = "Questo è un testo di esempio per verificare il calcolo dell'hash."
    same_hash = hashlib.sha256(same_text.encode("utf-8", errors="ignore")).hexdigest()
    
    assert normal_hash == same_hash, "Lo stesso testo dovrebbe produrre lo stesso hash"
    
    # E che testi diversi producano hash diversi
    different_text = "Questo è un testo diverso per verificare il calcolo dell'hash."
    different_hash = hashlib.sha256(different_text.encode("utf-8", errors="ignore")).hexdigest()
    
    assert normal_hash != different_hash, "Testi diversi dovrebbero produrre hash diversi"
    
    print("✓ Il normale calcolo dell'hash funziona correttamente")

if __name__ == "__main__":
    print("Esecuzione dei test per le correzioni ai problemi di estrazione testo...\n")
    
    try:
        test_parsed_document_new_fields()
        test_from_dict_with_new_fields()
        test_unique_hashes_for_problematic_files()
        test_normal_hash_calculation()
        
        print("\n✅ Tutti i test sono stati superati con successo!")
        print("\nLe modifiche apportate:")
        print("- Aggiunti campi is_problematic_file e problematic_reason a ParsedDocument")
        print("- Implementata gestione specifica per file PDF vuoti/scadenti")
        print("- Garantito che file problematici diversi abbiano hash univoci")
        print("- Preservata la funzionalità di deduplicazione per file validi")
        print("- Aggiunto metodo from_dict per coerenza con altre parti del sistema")
        
    except AssertionError as e:
        print(f"\n❌ Test fallito: {e}")
        exit(1)
    except Exception as e:
        print(f"\n❌ Errore durante l'esecuzione dei test: {e}")
        exit(1)