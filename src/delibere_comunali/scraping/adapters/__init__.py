"""
Package per gli adapter di scraping specifici per provider.

Adapter disponibili:
- base_adapter: Classe base per tutti gli adapter (contiene logica comune)
- halley_adapter: Per siti Halleyweb/OpenWeb
- maggioli_adapter: Per siti Maggioli/SIAP
- asmel_adapter: Per siti Asmel/AsmelNet
- kibernetes_adapter: Per siti Kibernetes
- sian_adapter: Per siti SIAN/System Engineering
- generic_adapter: Fallback per provider sconosciuti

Utilizzo:
    from delibere_comunali.scraping.adapters import (
        BaseAdapter,
        HalleyAdapter,
        MaggioliAdapter,
        AsmelAdapter,
        KibernetesAdapter,
        SianAdapter,
        GenericAdapter
    )
    from delibere_comunali.utils.adapter_detector import identify_comune_adapter

    # Rileva l'adapter appropriato
    adapter_info = identify_comune_adapter("Comune di Avella", url_albo="...")
    
    # Seleziona l'adapter in base al risultato
    adapter_map = {
        'halley_adapter': HalleyAdapter,
        'maggioli_adapter': MaggioliAdapter,
        'asmel_adapter': AsmelAdapter,
        'kibernetes_adapter': KibernetesAdapter,
        'sian_adapter': SianAdapter,
    }
    
    AdapterClass = adapter_map.get(adapter_info['adapter_principale'], GenericAdapter)
    adapter = AdapterClass()
"""

from .base_adapter import BaseAdapter
from .halley_adapter import HalleyAdapter
from .maggioli_adapter import MaggioliAdapter
from .asmel_adapter import AsmelAdapter
from .kibernetes_adapter import KibernetesAdapter
from .sian_adapter import SianAdapter
from .generic_adapter import GenericAdapter

__all__ = [
    'BaseAdapter',
    'HalleyAdapter',
    'MaggioliAdapter',
    'AsmelAdapter',
    'KibernetesAdapter',
    'SianAdapter',
    'GenericAdapter'
]
