"""
Test per il modulo adapter_detector.
Verifica che il rilevamento automatico degli adapter funzioni correttamente.
"""
import pytest
from unittest.mock import patch, MagicMock
import pandas as pd

from delibere_comunali.utils.adapter_detector import (
    AdapterDetector,
    identify_comune_adapter,
    batch_identify_adapters
)


class TestAdapterDetector:
    """Test per la classe AdapterDetector."""
    
    def test_detect_from_url_halley(self):
        """Test rilevamento Halleyweb dall'URL."""
        detector = AdapterDetector()
        
        # URL Halleyweb
        url = "https://servizi.comune.avella.av.it/openweb/albo/albo_pretorio.php"
        result = detector.detect_from_url(url)
        assert result == 'halley_adapter'
    
    def test_detect_from_url_maggioli(self):
        """Test rilevamento Maggioli dall'URL."""
        detector = AdapterDetector()
        
        # URL Maggioli
        url = "https://www.comune.test.it/maggioli/albo"
        result = detector.detect_from_url(url)
        assert result == 'maggioli_adapter'
    
    def test_detect_from_url_asmel(self):
        """Test rilevamento Asmel dall'URL."""
        detector = AdapterDetector()
        
        # URL Asmel
        url = "https://www.comune.test.it/asmelnet/albo"
        result = detector.detect_from_url(url)
        assert result == 'asmel_adapter'
    
    def test_detect_from_url_unknown(self):
        """Test rilevamento provider sconosciuto."""
        detector = AdapterDetector()
        
        # URL sconosciuto
        url = "https://www.comune.test.it/albo"
        result = detector.detect_from_url(url)
        assert result == 'generic_adapter'
    
    def test_detect_from_url_empty(self):
        """Test con URL vuoto."""
        detector = AdapterDetector()
        
        result = detector.detect_from_url("")
        assert result == 'unknown'
    
    def test_detect_from_url_none(self):
        """Test con URL None."""
        detector = AdapterDetector()
        
        result = detector.detect_from_url(None)
        assert result == 'unknown'
    
    def test_detect_albo_pretorio_pattern_halley_openweb(self):
        """Test rilevamento pattern Halley OpenWeb."""
        detector = AdapterDetector()
        
        url = "https://servizi.comune.avella.av.it/openweb/albo/albo_pretorio.php"
        result = detector.detect_albo_pretorio_pattern(url)
        assert result == 'halley_openweb'
    
    def test_detect_albo_pretorio_pattern_trasparenza(self):
        """Test rilevamento pattern Trasparenza Valutazione Merito."""
        detector = AdapterDetector()
        
        url = "https://trasparenza-valutazione-merito.it/albo"
        result = detector.detect_albo_pretorio_pattern(url)
        assert result == 'trasparenza_valutazione_merito'
    
    def test_detect_albo_pretorio_pattern_none(self):
        """Test con URL che non corrisponde a nessun pattern."""
        detector = AdapterDetector()
        
        url = "https://www.comune.test.it/albo"
        result = detector.detect_albo_pretorio_pattern(url)
        assert result is None


class TestIdentifyComuneAdapter:
    """Test per la funzione identify_comune_adapter."""
    
    def test_identify_halley_by_url(self):
        """Test identificazione comune con Halleyweb (solo URL)."""
        result = identify_comune_adapter(
            nome_comune="Avella",
            url_istituzionale="https://servizi.comune.avella.av.it/openweb",
            url_albo="https://servizi.comune.avella.av.it/openweb/albo/albo_pretorio.php"
        )
        
        assert result['nome_comune'] == "Avella"
        assert result['adapter_principale'] == 'halley_adapter'
        assert result['pattern_albo'] == 'halley_openweb'
        assert result['confidenza'] == 0.8
    
    def test_identify_unknown(self):
        """Test identificazione comune con provider sconosciuto."""
        result = identify_comune_adapter(
            nome_comune="Test",
            url_istituzionale="https://www.comune.test.it",
            url_albo="https://www.comune.test.it/albo"
        )
        
        assert result['nome_comune'] == "Test"
        assert result['adapter_principale'] == 'generic_adapter'
        assert result['confidenza'] == 0.3
    
    def test_identify_no_url(self):
        """Test identificazione senza URL."""
        result = identify_comune_adapter(
            nome_comune="Test",
            url_istituzionale="",
            url_albo=""
        )
        
        assert result['nome_comune'] == "Test"
        assert result['adapter_principale'] == 'unknown'
        assert result['confidenza'] == 0.1


class TestBatchIdentifyAdapters:
    """Test per la funzione batch_identify_adapters."""
    
    @patch('delibere_comunali.utils.adapter_detector.identify_comune_adapter')
    def test_batch_identify(self, mock_identify):
        """Test identificazione batch di comuni."""
        # Mock della funzione identify_comune_adapter
        def mock_identify_func(nome_comune, url_istituzionale="", url_albo=""):
            if "avella" in nome_comune.lower():
                return {
                    'nome_comune': nome_comune,
                    'adapter_principale': 'halley_adapter',
                    'pattern_albo': 'halley_openweb',
                    'confidenza': 0.8
                }
            else:
                return {
                    'nome_comune': nome_comune,
                    'adapter_principale': 'generic_adapter',
                    'pattern_albo': 'generic',
                    'confidenza': 0.3
                }
        
        mock_identify.side_effect = mock_identify_func
        
        # Crea un DataFrame di test
        data = {
            'nome_comune': ['Avella', 'Test1', 'Test2'],
            'url_istituzionale': [
                'https://servizi.comune.avella.av.it/openweb',
                'https://www.comune.test1.it',
                'https://www.comune.test2.it'
            ],
            'url_albo_pretorio': [
                'https://servizi.comune.avella.av.it/openweb/albo/albo_pretorio.php',
                'https://www.comune.test1.it/albo',
                'https://www.comune.test2.it/albo'
            ]
        }
        df = pd.DataFrame(data)
        
        results = batch_identify_adapters(df)
        
        assert len(results) == 3
        assert results[0]['nome_comune'] == 'Avella'
        assert results[0]['adapter_principale'] == 'halley_adapter'
        assert results[1]['adapter_principale'] == 'generic_adapter'
        assert results[2]['adapter_principale'] == 'generic_adapter'
