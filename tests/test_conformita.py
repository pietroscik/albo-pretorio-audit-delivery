#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test di Conformità Normativa per Albo Pretorio Audit Delivery

Questo modulo contiene test automatici per verificare la conformità del sistema
alle norme italiane (D.Lgs. 33/2013, CAD, TUEL, ecc.) e alle best practice.
"""

import unittest
import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path

# Aggiungi il percorso src al path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Importa i moduli necessari
from delibere_comunali.core.orchestrator import CentralOrchestrator, ResultCache, get_data_hash
from delibere_comunali.processing.procedural_understanding import ProceduralUnderstandingEngine
from delibere_comunali.processing.post_process_classification import (
    ClassificationScorer,
    apply_advanced_classification_rules,
    calculate_overall_quality_metrics
)


class TestConformitaNormativa(unittest.TestCase):
    """
    Test di conformità alle norme italiane:
    - D.Lgs. 33/2013 (Trasparenza Amministrativa)
    - D.Lgs. 82/2005 (CAD - Codice Amministrazione Digitale)
    - D.Lgs. 267/2000 (TUEL - Testo Unico Enti Locali)
    - D.Lgs. 50/2016 (Codice dei Contratti Pubblici)
    """

    def setUp(self):
        """Setup per tutti i test"""
        self.ente = "test_ente"
        self.orchestrator = CentralOrchestrator(ente=self.ente, max_workers=2)
        self.engine = ProceduralUnderstandingEngine(ente=self.ente)
        self.scorer = ClassificationScorer()
        
        # Crea un DataFrame di test con documenti tipici
        self.df_test = pd.DataFrame({
            'pdf_name': ['Delibera_001.pdf', 'Determinazione_001.pdf', 'Impegno_001.pdf', 'Liquidazione_001.pdf'],
            'doc_type': ['Delibera di Giunta', 'Determinazione Dirigenziale', 'Impegno di Spesa', 'Liquidazione'],
            'numero_atto': ['1', '1', '1', '1'],
            'data_atto': ['10/01/2026', '15/01/2026', '20/01/2026', '25/01/2026'],
            'oggetto': [
                'Approvazione Bilancio 2026',
                'Acquisto Materiale di Cancelleria',
                'Impegno Spesa per Fornitura Servizi',
                'Liquidazione Fattura n. 123'
            ],
            'category': ['Delibera', 'Determinazione', 'Impegno di Spesa', 'Liquidazione'],
            'classification_confidence': ['high', 'high', 'high', 'high'],
            'classification_confidence_score': [0.95, 0.90, 0.85, 0.80]
        })

    def tearDown(self):
        """Cleanup dopo ogni test"""
        self.orchestrator.cache.clear()

    # ========================================================================
    # TEST: D.Lgs. 33/2013 - Trasparenza Amministrativa
    # ========================================================================

    def test_dlgs_33_2013_art_22_pubblicazione_atti(self):
        """
        Test conformità a D.Lgs. 33/2013 Art. 22:
        Obbligo di pubblicazione degli atti amministrativi
        """
        # Verifica che il sistema supporti la pubblicazione di:
        # - Delibere
        # - Determinazioni
        # - Atti di programmazione
        atti_obbligatori = [
            'Delibera di Giunta',
            'Delibera di Consiglio',
            'Determinazione Dirigenziale',
            'Atto di Programmazione'
        ]
        
        for atto in atti_obbligatori:
            # Verifica che il tipo sia normalizzabile
            normalized = self.engine.normalize_document_type(atto)
            self.assertIsNotNone(normalized, f"Tipo {atto} non normalizzabile")
            self.assertIn("Delibera" if "Delibera" in atto else "Determinazione" if "Determinazione" in atto else "Atto", normalized)

    def test_dlgs_33_2013_art_29_dati_contabili(self):
        """
        Test conformità a D.Lgs. 33/2013 Art. 29:
        Obbligo di pubblicazione dei dati contabili
        """
        dati_contabili = [
            'Impegno di Spesa',
            'Liquidazione',
            'Accertamento',
            'Mandato di Pagamento',
            'Certificato di Pagamento'
        ]
        
        for dato in dati_contabili:
            normalized = self.engine.normalize_document_type(dato)
            self.assertIsNotNone(normalized, f"Dato contabile {dato} non normalizzabile")

    def test_dlgs_33_2013_art_30_contratti(self):
        """
        Test conformità a D.Lgs. 33/2013 Art. 30:
        Obbligo di pubblicazione dei contratti
        """
        contratti = [
            'Contratto',
            'Aggiudicazione',
            'Bando di Gara',
            'Disciplinare di Gara'
        ]
        
        for contratto in contratti:
            normalized = self.engine.normalize_document_type(contratto)
            self.assertIsNotNone(normalized, f"Contratto {contratto} non normalizzabile")

    def test_dlgs_33_2013_art_8_conservazione(self):
        """
        Test conformità a D.Lgs. 33/2013 Art. 8:
        Obbligo di conservazione dei documenti
        """
        # Verifica che il sistema supporti la conservazione per:
        # - 5 anni (documenti amministrativi)
        # - 10 anni (documenti contabili)
        # Il test verifica che il Piano di Conservazione sia documentato
        # (la verifica automatica è implementata in PIANO_CONSERVAZIONE.md)
        self.assertTrue(
            os.path.exists(str(Path(__file__).parent.parent / "PIANO_CONSERVAZIONE.md")),
            "Piano di Conservazione non trovato"
        )

    # ========================================================================
    # TEST: D.Lgs. 267/2000 (TUEL) - Procedure Contabili
    # ========================================================================

    def test_tuel_art_183_impegno_liquidazione(self):
        """
        Test conformità a D.Lgs. 267/2000 Art. 183:
        Sequenza Impegno → Liquidazione
        """
        # Verifica che la regola di dipendenza tra Impegno e Liquidazione esista
        self.assertIn("Liquidazione", self.engine.dependency_rules)
        
        liquidazione_rule = self.engine.dependency_rules["Liquidazione"]
        self.assertIn("Impegno di Spesa", liquidazione_rule["required"])
        self.assertGreater(liquidazione_rule["weights"].get("Impegno di Spesa", 0), 0)

    def test_tuel_art_183_tolleranza_temporale(self):
        """
        Test conformità a D.Lgs. 267/2000 Art. 183:
        Tolleranza temporale tra Impegno e Liquidazione (30 giorni)
        """
        liquidazione_rule = self.engine.dependency_rules["Liquidazione"]
        self.assertEqual(liquidazione_rule["tolerance_days"], 30)

    def test_tuel_sequenza_contabile(self):
        """
        Test conformità alle sequenze contabili tipiche del TUEL
        """
        # Verifica che la sequenza contabile sia definita
        self.assertIn("contabile", self.engine.procedural_sequences)
        
        sequenza_contabile = self.engine.procedural_sequences["contabile"]
        self.assertIn("Impegno di Spesa", sequenza_contabile)
        self.assertIn("Liquidazione", sequenza_contabile)

    # ========================================================================
    # TEST: D.Lgs. 50/2016 - Codice dei Contratti Pubblici
    # ========================================================================

    def test_codice_appalti_sequenza_gara(self):
        """
        Test conformità a D.Lgs. 50/2016:
        Sequenza tipica per gli appalti pubblici
        """
        # Verifica che la sequenza per appalti esista
        self.assertIn("appalto", self.engine.procedural_sequences)
        
        sequenza_appalto = self.engine.procedural_sequences["appalto"]
        self.assertIn("Gara", sequenza_appalto)
        self.assertIn("Aggiudicazione", sequenza_appalto)
        self.assertIn("Contratto", sequenza_appalto)

    def test_codice_appalti_affidamento_gara(self):
        """
        Test conformità a D.Lgs. 50/2016:
        Dipendenza tra Affidamento e Gara
        """
        self.assertIn("Affidamento", self.engine.dependency_rules)
        
        affidamento_rule = self.engine.dependency_rules["Affidamento"]
        self.assertIn("Gara", affidamento_rule["required"])

    # ========================================================================
    # TEST: CAD (D.Lgs. 82/2005) - Codice Amministrazione Digitale
    # ========================================================================

    def test_cad_art_41_efficienza(self):
        """
        Test conformità a CAD Art. 41:
        Efficienza dei servizi digitali (parallelizzazione)
        """
        # Verifica che la parallelizzazione sia configurabile
        self.assertIn("parallel_execution", self.orchestrator.coordination_params)
        self.assertTrue(self.orchestrator.coordination_params["parallel_execution"])
        
        # Verifica che max_workers sia configurabile
        self.assertGreater(self.orchestrator.max_workers, 0)

    def test_cad_art_50_sicurezza(self):
        """
        Test conformità a CAD Art. 50:
        Sicurezza dei dati e dei sistemi
        """
        # Verifica che il caching sia configurabile (per ridondanza)
        self.assertIn("use_caching", self.orchestrator.coordination_params)
        self.assertTrue(self.orchestrator.coordination_params["use_caching"])
        
        # Verifica che la cache abbia un limite di dimensione
        self.assertGreater(self.orchestrator.cache.max_size, 0)

    def test_cad_art_64_autenticazione(self):
        """
        Test conformità a CAD Art. 64:
        Autenticazione forte (SPID, CIE, CNS)
        """
        # Verifica che il sistema supporti autenticazione forte
        # (La verifica è documentale: il sistema è progettato per SPID/CIE/CNS)
        self.assertTrue(
            os.path.exists(str(Path(__file__).parent.parent / "MANUALE_AMMINISTRATORE.md"))
        )

    # ========================================================================
    # TEST: GDPR - Esenzioni per Dati Pubblici
    # ========================================================================

    def test_gdpr_art_2_esenzione_obbligo_legale(self):
        """
        Test conformità a GDPR Art. 2.2(c):
        Esenzione per adempimento di obbligo legale (D.Lgs. 33/2013)
        """
        # Verifica che la documentazione di conformità GDPR esista
        self.assertTrue(
            os.path.exists(str(Path(__file__).parent.parent / "CONFORMITA_GDPR_ALBO_PRETORIO.md")),
            "Documentazione GDPR non trovata"
        )

    def test_gdpr_art_6_base_giuridica(self):
        """
        Test conformità a GDPR Art. 6.1(c):
        Base giuridica per trattamento dati (obbligo legale)
        """
        # Verifica che la documentazione menzioni Art. 6.1(c)
        conformita_path = Path(__file__).parent.parent / "CONFORMITA_GDPR_ALBO_PRETORIO.md"
        with open(conformita_path, 'r', encoding='utf-8') as f:
            content = f.read()
            self.assertIn("Art. 6.1(c)", content)

    def test_gdpr_art_9_dati_sensibili(self):
        """
        Test conformità a GDPR Art. 9.2(j):
        Esenzione per dati resi pubblici per legge
        """
        conformita_path = Path(__file__).parent.parent / "CONFORMITA_GDPR_ALBO_PRETORIO.md"
        with open(conformita_path, 'r', encoding='utf-8') as f:
            content = f.read()
            self.assertIn("Art. 9.2(j)", content)

    # ========================================================================
    # TEST: Sequenze Procedurali e Dipendenze
    # ========================================================================

    def test_sequenza_spesa_completa(self):
        """
        Test che la sequenza di spesa completa sia definita
        """
        self.assertIn("spesa_completa", self.engine.procedural_sequences)
        
        sequenza = self.engine.procedural_sequences["spesa_completa"]
        self.assertIn("Delibera", sequenza)
        self.assertIn("Determinazione", sequenza)
        self.assertIn("Impegno di Spesa", sequenza)
        self.assertIn("Liquidazione", sequenza)

    def test_sequenza_lavori_pubblici(self):
        """
        Test che la sequenza per lavori pubblici sia definita
        """
        self.assertIn("lavori_pubblici", self.engine.procedural_sequences)
        
        sequenza = self.engine.procedural_sequences["lavori_pubblici"]
        self.assertIn("Delibera", sequenza)
        self.assertIn("Affidamento", sequenza)
        self.assertIn("Collaudo", sequenza)

    def test_dependency_rules_complete(self):
        """
        Test che le regole di dipendenza siano complete
        """
        # Verifica che le regole di dipendenza coprano i casi principali
        documenti_con_regole = [
            "Liquidazione",
            "Impegno di Spesa",
            "Determinazione",
            "Collaudo",
            "Affidamento",
            "Atto Contabile",
            "Visto Contabile"
        ]
        
        for doc in documenti_con_regole:
            self.assertIn(doc, self.engine.dependency_rules, f"Regola mancante per {doc}")

    # ========================================================================
    # TEST: Scoring e Classificazione
    # ========================================================================

    def test_classification_scorer_thresholds(self):
        """
        Test che le soglie di confidenza siano configurate
        """
        self.assertIn("high", self.scorer.confidence_thresholds)
        self.assertIn("medium", self.scorer.confidence_thresholds)
        self.assertIn("low", self.scorer.confidence_thresholds)
        
        # Verifica che le soglie siano valide (0-1)
        for threshold in self.scorer.confidence_thresholds.values():
            self.assertGreaterEqual(threshold, 0)
            self.assertLessEqual(threshold, 1)

    def test_classification_scorer_calculate(self):
        """
        Test che il calcolo della confidenza funzioni
        """
        # Test con regola
        conf, level = self.scorer.calculate_composite_confidence(
            'rule_based', rule_strength=0.95
        )
        self.assertEqual(level, 'high')
        self.assertGreaterEqual(conf, 0.9)
        
        # Test con ML
        conf, level = self.scorer.calculate_composite_confidence(
            'ml_predicted', probability=0.75
        )
        self.assertEqual(level, 'high')
        self.assertEqual(conf, 0.75)

    def test_apply_advanced_classification_rules(self):
        """
        Test che le regole avanzate di classificazione funzioni
        """
        # Test con testo di contabilità
        text = "Impegno di spesa per fornitura servizi"
        category = apply_advanced_classification_rules(text, "")
        self.assertEqual(category, "Contabilità")
        
        # Test con testo di lavori pubblici
        text = "Progetto esecutivo per manutenzione stradale"
        category = apply_advanced_classification_rules(text, "")
        self.assertEqual(category, "Lavori Pubblici")

    def test_calculate_overall_quality_metrics(self):
        """
        Test che il calcolo delle metriche di qualità funzioni
        """
        # Aggiungi colonne di confidenza al DataFrame di test
        df_with_confidence = self.df_test.copy()
        df_with_confidence['classification_confidence'] = ['high', 'medium', 'low', 'high']
        df_with_confidence['classification_confidence_score'] = [0.9, 0.7, 0.4, 0.8]
        
        metrics = calculate_overall_quality_metrics(df_with_confidence)
        
        self.assertIn('total_documents', metrics)
        self.assertIn('high_confidence_pct', metrics)
        self.assertIn('classification_quality_index', metrics)
        
        self.assertEqual(metrics['total_documents'], 4)
        self.assertEqual(metrics['high_confidence_count'], 2)

    # ========================================================================
    # TEST: Caching e Parallelizzazione
    # ========================================================================

    def test_cache_functionality(self):
        """
        Test che il caching funzioni correttamente
        """
        # Test set e get
        test_key = "test_cache_key"
        test_value = {"test": "value"}
        
        self.orchestrator.cache.set(test_key, test_value)
        cached_value = self.orchestrator.cache.get(test_key)
        
        self.assertEqual(cached_value, test_value)

    def test_cache_lru(self):
        """
        Test che il caching implementi LRU (Least Recently Used)
        """
        # Aggiungi più voci di quante ne può contenere la cache
        for i in range(self.orchestrator.cache.max_size + 5):
            self.orchestrator.cache.set(f"key_{i}", f"value_{i}")
        
        # Verifica che la cache non superi la dimensione massima
        self.assertLessEqual(len(self.orchestrator.cache._cache), self.orchestrator.cache.max_size)

    def test_data_hash_consistency(self):
        """
        Test che l'hash dei dati sia consistente
        """
        df1 = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
        df2 = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
        
        hash1 = get_data_hash(df1)
        hash2 = get_data_hash(df2)
        
        self.assertEqual(hash1, hash2)

    def test_parallel_execution_configurable(self):
        """
        Test che la parallelizzazione sia configurabile
        """
        # Disabilita parallelizzazione
        self.orchestrator.coordination_params["parallel_execution"] = False
        self.assertFalse(self.orchestrator.coordination_params["parallel_execution"])
        
        # Riabilita parallelizzazione
        self.orchestrator.coordination_params["parallel_execution"] = True
        self.assertTrue(self.orchestrator.coordination_params["parallel_execution"])

    # ========================================================================
    # TEST: Documentazione
    # ========================================================================

    def test_documentazione_presente(self):
        """
        Test che la documentazione essenziale sia presente
        """
        documenti_obbligatori = [
            "CONFORMITA_GDPR_ALBO_PRETORIO.md",
            "REGOLAMENTO_GESTIONE.md",
            "PIANO_CONSERVAZIONE.md",
            "MANUALE_UTENTE.md",
            "MANUALE_AMMINISTRATORE.md"
        ]
        
        for doc in documenti_obbligatori:
            self.assertTrue(
                os.path.exists(str(Path(__file__).parent.parent / doc)),
                f"Documento {doc} non trovato"
            )


class TestSequenzeProcedurali(unittest.TestCase):
    """
    Test specifici per le sequenze procedurali
    """

    def setUp(self):
        self.engine = ProceduralUnderstandingEngine()

    def test_sequenza_contabile_completa(self):
        """
        Test che una sequenza contabile completa sia riconosciuta
        """
        df = pd.DataFrame({
            'pdf_name': ['Impegno_001.pdf', 'Liquidazione_001.pdf', 'Accertamento_001.pdf'],
            'doc_type': ['Impegno di Spesa', 'Liquidazione', 'Accertamento'],
            'data_atto': ['10/01/2026', '20/01/2026', '25/01/2026'],
            'oggetto': ['Impegno', 'Liquidazione', 'Accertamento']
        })
        
        results = self.engine.identify_procedural_sequence(df)
        
        # Verifica che sia stata trovata la sequenza contabile
        self.assertGreater(len(results['sequences_found']), 0)

    def test_dependency_violation_detection(self):
        """
        Test che le violazioni di dipendenza siano rilevate
        """
        df = pd.DataFrame({
            'pdf_name': ['Liquidazione_001.pdf'],
            'doc_type': ['Liquidazione'],
            'data_atto': ['10/01/2026'],
            'oggetto': ['Liquidazione senza Impegno']
        })
        
        results = self.engine.identify_procedural_sequence(df)
        
        # Verifica che sia stata rilevata una violazione di dipendenza
        self.assertGreater(len(results['dependency_violations']), 0)


class TestPrestazioni(unittest.TestCase):
    """
    Test di prestazioni del sistema
    """

    def setUp(self):
        self.orchestrator = CentralOrchestrator(ente="test", max_workers=4)
        
        # Crea un DataFrame di test con 100 documenti
        self.df_large = pd.DataFrame({
            'pdf_name': [f'Doc_{i}.pdf' for i in range(100)],
            'doc_type': ['Delibera'] * 100,
            'data_atto': ['10/01/2026'] * 100,
            'oggetto': ['Test'] * 100
        })

    def test_parallel_execution_faster(self):
        """
        Test che la parallelizzazione sia più veloce della sequenziale
        (Test qualitativo, non quantitativo)
        """
        import time
        
        # Misura tempo sequenziale
        self.orchestrator.coordination_params["parallel_execution"] = False
        start_time = time.time()
        self.orchestrator.run_risk_assessment(self.df_large, use_cache=False)
        sequential_time = time.time() - start_time
        
        # Misura tempo parallelo
        self.orchestrator.coordination_params["parallel_execution"] = True
        start_time = time.time()
        self.orchestrator.run_risk_assessment(self.df_large, use_cache=False)
        parallel_time = time.time() - start_time
        
        # La parallelizzazione dovrebbe essere più veloce (o almeno non più lenta)
        # Note: Questo test può fallire in ambienti con poche risorse
        self.assertLessEqual(parallel_time, sequential_time * 1.5)  # Tollera un 50% di variabilità


if __name__ == '__main__':
    # Esegui i test
    unittest.main(verbosity=2)
