#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Modulo per scalare l'infrastruttura di audit degli albi pretori su scala nazionale.
Utilizza la mappatura ufficiale dei comuni italiani e gli adapter automatici.
"""

import sys
import os
import pandas as pd
import concurrent.futures
from pathlib import Path
from typing import List, Dict, Optional
import time
import logging

# Aggiungi il percorso src per importare i moduli
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from delibere_comunali.utils.comuni_anagrafica import carica_mappatura_esistente
from delibere_comunali.scraping.new_albo_scraper import AlboScraper, build_parser
from delibere_comunali.core.orchestrator import Orchestrator
from delibere_comunali.utils.config import get_tenant_dir

# Configura il logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class NationalInfrastructureScaler:
    """
    Classe per scalare l'infrastruttura di audit degli albi pretori su scala nazionale.
    """
    
    def __init__(self, mappatura_file: str = "mappatura_comuni_finale.csv"):
        """
        Inizializza lo scaler con la mappatura dei comuni.
        
        Args:
            mappatura_file: File con la mappatura dei comuni
        """
        self.mappatura = carica_mappatura_esistente(mappatura_file)
        if self.mappatura is None:
            raise ValueError(f"Impossibile caricare la mappatura da {mappatura_file}")
        
        logger.info(f"Mappatura caricata: {len(self.mappatura)} comuni")
    
    def process_single_comune(self, comune_data: Dict, max_pages: int = 5) -> Dict:
        """
        Processa un singolo comune.
        
        Args:
            comune_data: Dati del comune da processare
            max_pages: Numero massimo di pagine da elaborare
            
        Returns:
            Risultato del processamento
        """
        nome_comune = comune_data['nome_comune']
        logger.info(f"Inizio processamento comune: {nome_comune}")
        
        result = {
            'nome_comune': nome_comune,
            'codice_istat': comune_data.get('codice_istat', ''),
            'provincia': comune_data.get('provincia', ''),
            'adapter_usato': comune_data.get('scraper_adapter', 'unknown'),
            'stato': 'iniziato',
            'errori': [],
            'documenti_elaborati': 0,
            'tempo_elaborazione': 0
        }
        
        start_time = time.time()
        
        try:
            # Costruisci gli argomenti per lo scraper
            args = build_parser().parse_args([])
            args.ente = nome_comune
            args.out = str(get_tenant_dir(nome_comune))
            args.max_pages = max_pages
            args.delay = 1.0
            args.timeout = 20
            args.user_agent = "Mozilla/5.0 (compatible; CivicTechBot/1.0)"
            
            # Se abbiamo un URL specifico per l'albo pretorio, usalo
            if pd.notna(comune_data.get('url_albo_pretorio')) and comune_data['url_albo_pretorio']:
                args.start_url = comune_data['url_albo_pretorio']
            
            # Esegui lo scraping
            scraper = AlboScraper(args)
            scraper.run()
            
            # Conta i documenti elaborati
            output_dir = get_tenant_dir(nome_comune)
            pdf_dir = output_dir / "pdf"
            if pdf_dir.exists():
                result['documenti_elaborati'] = len(list(pdf_dir.glob("*.pdf")))
            
            result['stato'] = 'completato'
            
        except Exception as e:
            result['stato'] = 'errore'
            result['errori'].append(str(e))
            logger.error(f"Errore nel processamento di {nome_comune}: {e}")
        
        result['tempo_elaborazione'] = time.time() - start_time
        
        logger.info(f"Fine processamento {nome_comune}: stato={result['stato']}, "
                   f"documenti={result['documenti_elaborati']}, tempo={result['tempo_elaborazione']:.2f}s")
        
        return result
    
    def process_comuni_batch(self, comuni_list: List[Dict], max_workers: int = 5) -> List[Dict]:
        """
        Processa un batch di comuni in parallelo.
        
        Args:
            comuni_list: Lista di dizionari con i dati dei comuni
            max_workers: Numero massimo di worker paralleli
            
        Returns:
            Lista di risultati
        """
        results = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit tutti i task
            future_to_comune = {
                executor.submit(self.process_single_comune, comune): comune 
                for comune in comuni_list
            }
            
            # Raccogli i risultati man mano che completano
            for future in concurrent.futures.as_completed(future_to_comune):
                result = future.result()
                results.append(result)
        
        return results
    
    def scale_by_province(self, province_selezionate: Optional[List[str]] = None, 
                         max_comuni_per_province: int = 10, max_workers: int = 3) -> pd.DataFrame:
        """
        Scala l'infrastruttura processando comuni raggruppati per provincia.
        
        Args:
            province_selezionate: Lista di province da processare (None = tutte)
            max_comuni_per_province: Numero massimo di comuni per provincia
            max_workers: Numero massimo di worker paralleli
            
        Returns:
            DataFrame con i risultati
        """
        logger.info("Inizio scaling per provincia")
        
        # Filtra i comuni per provincia
        if province_selezionate:
            comuni_filtrati = self.mappatura[self.mappatura['provincia'].isin(province_selezionate)]
        else:
            comuni_filtrati = self.mappatura
        
        # Raggruppa per provincia e seleziona un certo numero di comuni per provincia
        comuni_da_processare = []
        
        for provincia in comuni_filtrati['provincia'].unique():
            comuni_prov = comuni_filtrati[comuni_filtrati['provincia'] == provincia].head(max_comuni_per_province)
            comuni_da_processare.extend(comuni_prov.to_dict('records'))
        
        logger.info(f"Comuni selezionati per il processamento: {len(comuni_da_processare)}")
        
        # Processa i comuni
        results = self.process_comuni_batch(comuni_da_processare, max_workers)
        
        # Converti in DataFrame
        results_df = pd.DataFrame(results)
        
        return results_df
    
    def scale_by_adapter(self, adapter_selezionati: Optional[List[str]] = None, 
                        max_comuni_per_adapter: int = 10, max_workers: int = 3) -> pd.DataFrame:
        """
        Scala l'infrastruttura processando comuni raggruppati per tipo di adapter.
        
        Args:
            adapter_selezionati: Lista di adapter da processare (None = tutti)
            max_comuni_per_adapter: Numero massimo di comuni per adapter
            max_workers: Numero massimo di worker paralleli
            
        Returns:
            DataFrame con i risultati
        """
        logger.info("Inizio scaling per adapter")
        
        # Filtra i comuni per adapter
        if adapter_selezionati:
            comuni_filtrati = self.mappatura[self.mappatura['scraper_adapter'].isin(adapter_selezionati)]
        else:
            comuni_filtrati = self.mappatura
        
        # Raggruppa per adapter e seleziona un certo numero di comuni per adapter
        comuni_da_processare = []
        
        for adapter in comuni_filtrati['scraper_adapter'].unique():
            comuni_adapt = comuni_filtrati[comuni_filtrati['scraper_adapter'] == adapter].head(max_comuni_per_adapter)
            comuni_da_processare.extend(comuni_adapt.to_dict('records'))
        
        logger.info(f"Comuni selezionati per il processamento: {len(comuni_da_processare)}")
        
        # Processa i comuni
        results = self.process_comuni_batch(comuni_da_processare, max_workers)
        
        # Converti in DataFrame
        results_df = pd.DataFrame(results)
        
        return results_df
    
    def generate_scaling_report(self, results_df: pd.DataFrame, output_file: str = "scaling_report.csv"):
        """
        Genera un report di scaling con le statistiche.
        
        Args:
            results_df: DataFrame con i risultati del scaling
            output_file: File di output per il report
        """
        # Calcola le statistiche
        stats = {
            'totale_comuni': len(results_df),
            'comuni_successo': len(results_df[results_df['stato'] == 'completato']),
            'comuni_errore': len(results_df[results_df['stato'] == 'errore']),
            'documenti_totali': results_df['documenti_elaborati'].sum(),
            'tempo_medio': results_df['tempo_elaborazione'].mean(),
            'tempo_totale': results_df['tempo_elaborazione'].sum()
        }
        
        # Aggiungi statistiche per provincia
        prov_stats = results_df.groupby('provincia').agg({
            'stato': ['count', lambda x: (x == 'completato').sum()],
            'documenti_elaborati': 'sum',
            'tempo_elaborazione': 'mean'
        }).round(2)
        
        # Aggiungi statistiche per adapter
        adapter_stats = results_df.groupby('adapter_usato').agg({
            'stato': ['count', lambda x: (x == 'completato').sum()],
            'documenti_elaborati': 'sum',
            'tempo_elaborazione': 'mean'
        }).round(2)
        
        # Salva il report
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("REPORT SCALING INFRASTRUTTURA ALBO PRETORIO NAZIONALE\n")
            f.write("=" * 60 + "\n\n")
            
            f.write("STATISTICHE GENERALI:\n")
            for key, value in stats.items():
                f.write(f"  {key}: {value}\n")
            
            f.write(f"\nSTATISTICHE PER PROVINCIA:\n")
            f.write(prov_stats.to_string())
            
            f.write(f"\n\nSTATISTICHE PER ADAPTER:\n")
            f.write(adapter_stats.to_string())
        
        logger.info(f"Report di scaling salvato in: {output_file}")
        
        return stats

def main():
    print("=== Scaling Infrastruttura Albo Pretorio Nazionale ===")
    
    # Inizializza lo scaler
    try:
        scaler = NationalInfrastructureScaler()
    except Exception as e:
        print(f"Errore nell'inizializzazione dello scaler: {e}")
        return
    
    # Esempio: scala per alcune province specifiche
    print("\n1. Esempio: Scaling per alcune province (AV, BN, CE)")
    results_prov = scaler.scale_by_province(['AV', 'BN', 'CE'], max_comuni_per_province=3, max_workers=2)
    
    print(f"   Risultati: {len(results_prov)} comuni processati")
    print(f"   Successi: {(results_prov['stato'] == 'completato').sum()}")
    print(f"   Errori: {(results_prov['stato'] == 'errore').sum()}")
    
    # Esempio: scala per alcuni adapter specifici
    print("\n2. Esempio: Scaling per adapter Halley")
    results_adapter = scaler.scale_by_adapter(['halley_adapter'], max_comuni_per_adapter=5, max_workers=2)
    
    print(f"   Risultati: {len(results_adapter)} comuni processati")
    print(f"   Successi: {(results_adapter['stato'] == 'completato').sum()}")
    print(f"   Errori: {(results_adapter['stato'] == 'errore').sum()}")
    
    # Genera report
    print("\n3. Generazione report di scaling...")
    combined_results = pd.concat([results_prov, results_adapter], ignore_index=True)
    stats = scaler.generate_scaling_report(combined_results, "scaling_report.csv")
    
    print(f"\n4. Statistiche finali:")
    for key, value in stats.items():
        print(f"   {key}: {value}")
    
    print("\n=== Scaling Completato ===")
    print("\nFile generati:")
    print("- scaling_report.csv: Report completo delle operazioni di scaling")

if __name__ == "__main__":
    main()