#!/usr/bin/env python3
"""
Albo Pretorio Audit Delivery - Unit Tests
25 unit tests per le funzionalità di analisi e filtering
"""

import unittest
import sys
import os
import tempfile
from pathlib import Path
import pandas as pd
from unittest.mock import patch

# Assicuriamoci che i file importati vengano trovati
sys.path.append(str(Path(__file__).resolve().parent))

from analyze_albo import (
    is_accounting_relevant,
    is_personnel_competence_relevant,
    extract_personnel_competences,
    extract_decree_references,
    extract_full_metadata,
    process_directory_to_csv,
    PERSONNEL_PATTERNS,
    COMPILED_PATTERNS
)
from src.web.rag_chat import esegui_query_rag_core


class TestAccountingRelevance(unittest.TestCase):
    """Test per il rilevamento di rilevanza contabile."""

    def test_appalto_diretto(self):
        """Test rilevamento appalto diretto."""
        text = "Appalto diretto per forniture di ufficio"
        self.assertTrue(is_accounting_relevant(text, "Determinazione", "Contabilità"))

    def test_cig_pattern(self):
        """Test rilevamento pattern CIG."""
        text = "CIG: 1234567890"
        self.assertTrue(is_accounting_relevant(text, "Determinazione", "Lavori Pubblici"))

    def test_impegno_spesa(self):
        """Test rilevamento impegno di spesa."""
        text = "Impegno di spesa per il progetto X"
        self.assertTrue(is_accounting_relevant(text, "Determinazione", "Affari Generali"))

    def test_liquidazione(self):
        """Test rilevamento liquidazione."""
        text = "Liquidazione della fattura n. 123"
        self.assertTrue(is_accounting_relevant(text, "Determinazione", "Personale"))

    def test_capitolo(self):
        """Test rilevamento capitolo."""
        text = "Capitolo 1234 del bilancio"
        self.assertTrue(is_accounting_relevant(text, "Determinazione", "Contabilità"))

    def test_non_accounting_text(self):
        """Test testo non contabile."""
        text = "Questo è un documento generico senza riferimenti"
        self.assertFalse(is_accounting_relevant(text, "Avviso", "Pubblicazione e Trasparenza"))


class TestPersonnelCompetenceRelevance(unittest.TestCase):
    """Test per il rilevamento di rilevanza competenze del personale."""

    def test_decreto_sindacale(self):
        """Test rilevamento Decreto Sindacale."""
        text = "Decreto Sindacale n. 123/2024"
        self.assertTrue(is_personnel_competence_relevant(text))

    def test_funzioni_dirigenziali(self):
        """Test rilevamento funzioni dirigenziali."""
        text = "Attribuzione funzioni dirigenziali al dott. Rossi"
        self.assertTrue(is_personnel_competence_relevant(text))

    def test_ufficio(self):
        """Test rilevamento ufficio."""
        text = "Ufficio Tecnico Comunale"
        self.assertTrue(is_personnel_competence_relevant(text))

    def test_profilo_professionale(self):
        """Test rilevamento profilo professionale."""
        text = "Profilo professionale Contabile"
        self.assertTrue(is_personnel_competence_relevant(text))

    def test_dlgs_165(self):
        """Test rilevamento D.lgs. 165/2001."""
        text = "Ai sensi del D.lgs. 165/2001"
        self.assertTrue(is_personnel_competence_relevant(text))

    def test_ccnl(self):
        """Test rilevamento CCNL 16.11.2022."""
        text = "Contratto Collettivo Nazionale di Lavoro 16.11.2022"
        self.assertTrue(is_personnel_competence_relevant(text))

    def test_non_personnel_text(self):
        """Test testo non rilevante per competenze del personale."""
        text = "Questo è un documento senza riferimenti a competenze del personale"
        self.assertFalse(is_personnel_competence_relevant(text))


class TestExtractionFunctions(unittest.TestCase):
    """Test per le funzioni di estrazione."""

    def test_extract_decree_references(self):
        """Test estrazione riferimenti a decreti."""
        text = "Decreto Sindacale n. 123/2024 e Decreto Sindacale prot. n. 456"
        references = extract_decree_references(text)
        self.assertEqual(len(references), 2)
        self.assertEqual(references[0]['number'], '123/2024')
        self.assertEqual(references[1]['number'], '456')

    def test_extract_personnel_competences_decree(self):
        """Test estrazione competenze - decreto."""
        text = "Decreto Sindacale n. 123/2024"
        competences = extract_personnel_competences(text)
        self.assertGreater(len(competences), 0)
        self.assertEqual(competences[0].competence_type, "decreto_sindacale")
        self.assertEqual(competences[0].assigned_to, "Sindaco")

    def test_extract_personnel_competences_office(self):
        """Test estrazione competenze - ufficio."""
        text = "Ufficio Tecnico"
        competences = extract_personnel_competences(text)
        self.assertGreater(len(competences), 0)
        self.assertEqual(competences[0].competence_type, "ufficio")

    def test_extract_personnel_competences_dirigenziali(self):
        """Test estrazione competenze - funzioni dirigenziali."""
        text = "funzioni dirigenziali attribuite"
        competences = extract_personnel_competences(text)
        self.assertGreater(len(competences), 0)
        self.assertEqual(competences[0].competence_type, "funzioni_dirigenziali")


class TestFullMetadataExtraction(unittest.TestCase):
    """Test per l'estrazione completa dei metadati."""

    @patch('analyze_albo.extract_text_pdf')
    def test_extract_full_metadata_determinazione(self, mock_extract):
        """Test estrazione metadati per Determinazione."""
        mock_extract.return_value = "Determinazione n. 123 - Appalto diretto con impegno di spesa. " * 20
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            temp_path = Path(f.name)
        try:
            metadata = extract_full_metadata(temp_path)
            self.assertEqual(metadata['doc_type'], "Determinazione")
            self.assertTrue(metadata['accounting_relevant'])
        finally:
            temp_path.unlink()

    @patch('analyze_albo.extract_text_pdf')
    def test_extract_full_metadata_delibera(self, mock_extract):
        """Test estrazione metadati per Delibera."""
        mock_extract.return_value = "Delibera di Giunta n. 456 - attribuzione funzioni dirigenziali. " * 20
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            temp_path = Path(f.name)
        try:
            metadata = extract_full_metadata(temp_path)
            self.assertEqual(metadata['doc_type'], "Delibera")
            self.assertTrue(metadata['is_personnel_competence_relevant'])
        finally:
            temp_path.unlink()


class TestProcessDirectory(unittest.TestCase):
    """Test per il processamento della directory."""

    @patch('analyze_albo.extract_text_pdf')
    def test_process_directory_to_csv(self, mock_extract):
        """Test processamento directory in CSV."""
        mock_extract.return_value = "Determinazione con impegno di spesa e CIG 1234567890. " * 20
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            (temp_path / "Determinazione_1.pdf").touch()
            (temp_path / "Delibera_2.pdf").touch()

            output_csv = temp_path / "output.csv"
            df = process_directory_to_csv(temp_path, output_csv)

            self.assertEqual(len(df), 2)
            self.assertTrue(output_csv.exists())

            csv_df = pd.read_csv(output_csv)
            self.assertEqual(len(csv_df), 2)


class TestRAGChat(unittest.TestCase):
    """Test per il modulo RAG integrato (esegui_query_rag_core)."""

    def test_rag_chat_initialization(self):
        """Test inizializzazione RAG Chat."""
        risultato = esegui_query_rag_core("test", "avella")
        self.assertIsInstance(risultato, str)

    @patch('src.web.rag_chat._load_corpus_documents')
    def test_rag_chat_load_documents(self, mock_load):
        """Test caricamento documenti in RAG Chat."""
        # Simula che il corpus esista e contenga documenti
        mock_load.return_value = [
            unittest.mock.Mock(page_content="doc1 content", metadata={'accounting_relevant': True}),
            unittest.mock.Mock(page_content="doc2 content", metadata={'accounting_relevant': False})
        ]
        
        # Questo test verifica che la funzione non vada in errore se il corpus è presente
        # Il risultato effettivo dipende dalla presenza di una chiave API valida
        risultato = esegui_query_rag_core("test", "avella")
        self.assertIsInstance(risultato, str)


    def test_rag_chat_query_personnel_only(self):
        """Test query RAG con filtro solo competenze del personale."""
        # Assicuriamoci che l'errore venga gestito elegantemente se non c'è l'indice locale (ambiente di test)
        risultato = esegui_query_rag_core(
            query="competenze personale",
            ente="ente_di_test_inesistente_123",
            only_personnel_competence=True,
            k=1
        )
        self.assertIsInstance(risultato, str)
        self.assertTrue("non" in risultato.lower() or "nessun" in risultato.lower(), f"Il messaggio di fallback non contiene 'non' o 'nessun': '{risultato}'")


class TestPatternCoverage(unittest.TestCase):
    """Test copertura pattern."""

    def test_personnel_patterns_count(self):
        """Test numero pattern competenze personale."""
        self.assertGreater(len(PERSONNEL_PATTERNS), 0)
        self.assertGreaterEqual(len(PERSONNEL_PATTERNS), 15)

    def test_compiled_patterns(self):
        """Test che tutti i pattern siano compilati."""
        self.assertEqual(len(COMPILED_PATTERNS), len(PERSONNEL_PATTERNS))
        for key in PERSONNEL_PATTERNS:
            self.assertIn(key, COMPILED_PATTERNS)


class TestExtendedPatterns(unittest.TestCase):
    """Test per i nuovi pattern estesi."""

    def test_determinazione_patterns(self):
        """Test pattern specifici per Determine."""
        from src.patterns.albo_patterns import DETERMINAZIONE_PATTERNS
        text = "Determinazione n. 370 - impegno di spesa per appalto diretto"
        matched = any(pattern.search(text) for pattern in DETERMINAZIONE_PATTERNS.values())
        self.assertTrue(matched, "Nessun pattern Determinazione ha matchato")

    def test_delibera_patterns(self):
        """Test pattern specifici per Delibere."""
        from src.patterns.albo_patterns import DELIBERA_PATTERNS
        text = "Delibera di Giunta - Piano Triennale Fabbisogno Personale 2026/2028"
        matched = any(pattern.search(text) for pattern in DELIBERA_PATTERNS.values())
        self.assertTrue(matched, "Nessun pattern Delibera ha matchato")

    def test_ordinanza_patterns(self):
        """Test pattern specifici per Ordinanze."""
        from src.patterns.albo_patterns import ORDINANZA_PATTERNS
        text = "Ordinanza Sindacale n. 26 - attribuzione funzioni"
        matched = any(pattern.search(text) for pattern in ORDINANZA_PATTERNS.values())
        self.assertTrue(matched, "Nessun pattern Ordinanza ha matchato")

    def test_numeraria_patterns(self):
        """Test pattern specifici per Numeraria."""
        from src.patterns.albo_patterns import NUMERARIA_PATTERNS
        text = "Impegno di spesa di € 1.377,68 per oneri SUA"
        matched = any(pattern.search(text) for pattern in NUMERARIA_PATTERNS.values())
        self.assertTrue(matched, "Nessun pattern Numeraria ha matchato")

    def test_atto_patterns(self):
        """Test pattern specifici per Atti."""
        from src.patterns.albo_patterns import ATTO_PATTERNS
        text = "Atto - trattamento in servizio ai sensi della Legge 207/2024"
        matched = any(pattern.search(text) for pattern in ATTO_PATTERNS.values())
        self.assertTrue(matched, "Nessun pattern Atto ha matchato")

    def test_avviso_patterns(self):
        """Test pattern specifici per Avvisi."""
        from src.patterns.albo_patterns import AVVISO_PATTERNS
        text = "Avviso di selezione interna per progressioni economiche"
        matched = any(pattern.search(text) for pattern in AVVISO_PATTERNS.values())
        self.assertTrue(matched, "Nessun pattern Avviso ha matchato")

    def test_bando_patterns(self):
        """Test pattern specifici per Bandi."""
        from src.patterns.albo_patterns import BANDO_PATTERNS
        text = "Bando di gara per appalto lavori CIG: 1234567890"
        matched = any(pattern.search(text) for pattern in BANDO_PATTERNS.values())
        self.assertTrue(matched, "Nessun pattern Bando ha matchato")

    def test_extract_cig_cup(self):
        """Test estrazione CIG e CUP."""
        from src.patterns.albo_patterns import extract_cig_cup
        text = "CIG: 1234567890 e CUP: ABC123456789012"
        result = extract_cig_cup(text)
        self.assertEqual(result['cig'], '1234567890')
        self.assertEqual(result['cup'], 'ABC123456789012')

    def test_extract_importi(self):
        """Test estrazione importi."""
        from src.patterns.albo_patterns import extract_importi
        text = "Importo totale: € 1.377,68 e IVA: € 250,00"
        importi = extract_importi(text)
        self.assertGreater(len(importi), 0)
        self.assertIn(1377.68, importi)
        self.assertIn(250.00, importi)

    def test_extract_date(self):
        """Test estrazione date."""
        from src.patterns.albo_patterns import extract_date
        text = "Data: 26/05/2026 e scadenza: 10/07/2025"
        date = extract_date(text)
        self.assertEqual(len(date), 2)
        self.assertIn('26/05/2026', date)
        self.assertIn('10/07/2025', date)

    def test_extract_nomi_propri(self):
        """Test estrazione nomi propri."""
        from src.patterns.albo_patterns import extract_nomi_propri
        text = "Responsabile: DOTT. PASQUALE MAIELLA e Fornitore: NATALE BERNARDO S.R.L."
        nomi = extract_nomi_propri(text)
        self.assertGreater(len(nomi), 0)
        self.assertTrue(any('PASQUALE MAIELLA' in n.upper() for n in nomi))


if __name__ == '__main__':
    # Output encoding fisso per supporto log su Windows
    if hasattr(sys.stdout, 'reconfigure') and sys.stdout.encoding.lower() != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')
        
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    for test_class in [
        TestAccountingRelevance,
        TestPersonnelCompetenceRelevance,
        TestExtractionFunctions,
        TestFullMetadataExtraction,
        TestProcessDirectory,
        TestRAGChat,
        TestPatternCoverage,
        TestExtendedPatterns,  # Nuovi test
    ]:
        suite.addTests(loader.loadTestsFromTestCase(test_class))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")

    if result.wasSuccessful():
        print("\n✅ All tests passed!")
    else:
        print("\n❌ Some tests failed!")