#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Modulo di calcolo KPI manageriali per il sistema di audit dell'albo pretorio
Implementa indicatori di efficienza, efficacia, economicità e trasparenza
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import logging
from datetime import datetime
import json
import seaborn as sns
import matplotlib.pyplot as plt
from scipy import stats
from dateutil.relativedelta import relativedelta
import argparse

# Configura il logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MunicipalManagementKPI:
    """
    Classe per il calcolo dei KPI manageriali per il controllo di gestione
    """
    
    def __init__(self):
        self.kpi_categories = {
            'efficienza': self._calcola_efficienza,
            'efficacia': self._calcola_efficacia,
            'economicita': self._calcola_economicita,
            'trasparenza': self._calcola_trasparenza
        }
    
    def _calcola_efficienza(self, delibere_data: pd.DataFrame) -> Dict:
        """
        Calcola KPI di efficienza:
        - Tempo medio approvazione delibere
        - Velocità di trattamento
        - Utilizzo risorse
        """
        kpi_efficienza = {}
        
        # Conversione date se necessario
        if 'data_atto' in delibere_data.columns:
            delibere_data['data_atto'] = pd.to_datetime(
                delibere_data['data_atto'], 
                format='%d/%m/%Y', 
                errors='coerce'
            )
        
        # Calcola tempo medio approvazione se ci sono date
        if 'data_atto' in delibere_data.columns:
            valid_dates = delibere_data.dropna(subset=['data_atto'])
            if not valid_dates.empty:
                # Assumiamo una data di presentazione ipotetica per calcolare i tempi
                # In mancanza di date di presentazione, usiamo una logica basata su gruppi
                valid_dates = valid_dates.sort_values('data_atto')
                
                # Calcola differenza tra date successive come proxy per tempi di lavorazione
                valid_dates = valid_dates.copy()
                valid_dates['next_date'] = valid_dates['data_atto'].shift(-1)
                valid_dates['tempo_lavorazione_gg'] = (
                    valid_dates['next_date'] - valid_dates['data_atto']
                ).dt.days
                
                tempo_medio = valid_dates['tempo_lavorazione_gg'].mean()
                kpi_efficienza['tempo_medio_approvazione_gg'] = round(tempo_medio, 2) if not pd.isna(tempo_medio) else 0.0
        
        # Calcola volumetria mensile
        if 'data_atto' in delibere_data.columns:
            delibere_data['anno_mese'] = delibere_data['data_atto'].dt.to_period('M')
            volumetria_mensile = delibere_data.groupby('anno_mese').size()
            kpi_efficienza['volumetria_media_mensile'] = round(volumetria_mensile.mean(), 2) if not volumetria_mensile.empty else 0.0
            kpi_efficienza['dev_std_volumetria'] = round(volumetria_mensile.std(), 2) if not volumetria_mensile.empty else 0.0
        
        # Indice di concentrazione temporale (misura di affollamento)
        if 'data_atto' in delibere_data.columns:
            giorni_lavoro = delibere_data.groupby(delibere_data['data_atto'].dt.date).size()
            if not giorni_lavoro.empty:
                concentrazione = giorni_lavoro.std() / giorni_lavoro.mean() if giorni_lavoro.mean() != 0 else 0
                kpi_efficienza['indice_concentrazione_temporale'] = round(concentrazione, 4)
        
        return kpi_efficienza
    
    def _calcola_efficacia(self, delibere_data: pd.DataFrame) -> Dict:
        """
        Calcola KPI di efficacia:
        - Percentuale obiettivi raggiunti
        - Copertura aree di competenza
        - Qualità delle decisioni
        """
        kpi_efficacia = {}
        
        # Percentuale di documenti con categorie assegnate
        if 'category' in delibere_data.columns:
            categorie_assegnate = delibere_data['category'].notna() & (delibere_data['category'] != '') & (delibere_data['category'] != 'nan')
            perc_categoria = (categorie_assegnate.sum() / len(delibere_data)) * 100
            kpi_efficacia['perc_documenti_classificati'] = round(perc_categoria, 2)
        
        # Distribuzione per categoria (indicatore di copertura aree)
        if 'category' in delibere_data.columns:
            distribuzione_categorie = delibere_data['category'].value_counts(normalize=True) * 100
            kpi_efficacia['distribuzione_categorie'] = distribuzione_categorie.to_dict()
        
        # Qualità basata su dati completi
        campi_obbligatori = ['importo_max', 'beneficiario', 'responsabile', 'oggetto']
        campi_compilati = 0
        for campo in campi_obbligatori:
            if campo in delibere_data.columns:
                campi_compilati += delibere_data[campo].notna().sum()
        
        totale_campi_possibili = len(delibere_data) * len(campi_obbligatori)
        qualita_dati = (campi_compilati / totale_campi_possibili) * 100 if totale_campi_possibili > 0 else 0
        kpi_efficacia['qualita_compilazione_dati_%'] = round(qualita_dati, 2)
        
        return kpi_efficacia
    
    def _calcola_economicita(self, delibere_data: pd.DataFrame) -> Dict:
        """
        Calcola KPI di economicità:
        - Distribuzione spesa per settore
        - Concentrazione fornitori (indice HHI)
        - Efficienza allocativa
        """
        kpi_economicita = {}
        
        # Distribuzione spesa per settore
        if 'category' in delibere_data.columns and 'importo_max' in delibere_data.columns:
            spesa_per_categoria = delibere_data.groupby('category')['importo_max'].sum().fillna(0)
            spesa_totale = spesa_per_categoria.sum()
            if spesa_totale > 0:
                distribuzione_spesa = (spesa_per_categoria / spesa_totale) * 100
                kpi_economicita['distribuzione_spesa_percentuale'] = distribuzione_spesa.to_dict()
                kpi_economicita['spesa_totale'] = round(spesa_totale, 2)
        
        # Indice HHI (Herfindahl-Hirschman) per concentrazione fornitori
        if 'beneficiario' in delibere_data.columns and 'importo_max' in delibere_data.columns:
            # Rimuovi beneficiari nulli o non validi
            valid_data = delibere_data[
                (delibere_data['beneficiario'].notna()) & 
                (delibere_data['beneficiario'] != '') & 
                (delibere_data['beneficiario'] != 'nan') &
                (delibere_data['importo_max'].notna()) &
                (delibere_data['importo_max'] > 0)
            ].copy()
            
            if not valid_data.empty:
                spesa_per_fornitore = valid_data.groupby('beneficiario')['importo_max'].sum()
                spesa_totale = spesa_per_fornitore.sum()
                
                if spesa_totale > 0:
                    quote = spesa_per_fornitore / spesa_totale
                    hhi = (quote ** 2).sum() * 10000  # Scala 0-10000
                    kpi_economicita['indice_concentrazione_hhi'] = round(hhi, 2)
                    
                    # Dettaglio top fornitori
                    top_fornitori = spesa_per_fornitore.nlargest(10)
                    kpi_economicita['top_10_fornitori'] = top_fornitori.to_dict()
        
        # Efficienza allocativa (spesa media per tipo documento)
        if 'doc_type' in delibere_data.columns and 'importo_max' in delibere_data.columns:
            spesa_per_tipo = delibere_data.groupby('doc_type')['importo_max'].agg(['mean', 'sum', 'count']).round(2)
            kpi_economicita['efficienza_allocativa'] = spesa_per_tipo.to_dict('index')
        
        return kpi_economicita
    
    def _calcola_trasparenza(self, delibere_data: pd.DataFrame) -> Dict:
        """
        Calcola KPI di trasparenza:
        - Completezza informazioni
        - Accessibilità documenti
        - Tempestività pubblicazione
        """
        kpi_trasparenza = {}
        
        # Indice di completezza (percentuale di campi compilati)
        campi_interesse = ['cig', 'cup', 'importo_max', 'beneficiario', 'responsabile', 'oggetto']
        campi_compilati_totali = 0
        for campo in campi_interesse:
            if campo in delibere_data.columns:
                campi_compilati_totali += delibere_data[campo].notna().sum()
        
        totale_campi_possibili = len(delibere_data) * len(campi_interesse)
        completezza = (campi_compilati_totali / totale_campi_possibili) * 100 if totale_campi_possibili > 0 else 0
        kpi_trasparenza['indice_completezza_%'] = round(completezza, 2)
        
        # Presenza di codici identificativi
        if 'cig' in delibere_data.columns:
            perc_cig = (delibere_data['cig'].notna() & (delibere_data['cig'] != '') & (delibere_data['cig'] != 'nan')).mean() * 100
            kpi_trasparenza['perc_documenti_con_cig_%'] = round(perc_cig, 2)
        
        if 'cup' in delibere_data.columns:
            perc_cup = (delibere_data['cup'].notna() & (delibere_data['cup'] != '') & (delibere_data['cup'] != 'nan')).mean() * 100
            kpi_trasparenza['perc_documenti_con_cup_%'] = round(perc_cup, 2)
        
        # Accessibilità documenti (se esiste colonna che indica lo stato)
        if 'is_accessible' in delibere_data.columns:
            perc_accessibili = delibere_data['is_accessible'].mean() * 100
            kpi_trasparenza['perc_documenti_accessibili_%'] = round(perc_accessibili, 2)
        
        # Qualità testo (se esiste una metrica di qualità testo)
        if 'text_chars' in delibere_data.columns:
            # Documenti con testo sufficientemente lungo da essere considerato valido
            testo_abbastanza_lungo = (delibere_data['text_chars'] >= 500).mean() * 100
            kpi_trasparenza['perc_documenti_testo_valido_%'] = round(testo_abbastanza_lungo, 2)
        
        return kpi_trasparenza
    
    def generate_dashboard(self, delibere_data: pd.DataFrame) -> Dict:
        """
        Dashboard KPI per controllo di gestione:
        - Tempo medio approvazione delibere
        - Distribuzione spesa per settore
        - Concentrazione fornitori (indice HHI)
        - Compliance procedure affidamento
        """
        logger.info(f"Calcolo KPI per {len(delibere_data)} documenti")
        
        # Calcola tutte le categorie di KPI
        efficienza = self._calcola_efficienza(delibere_data)
        efficacia = self._calcola_efficacia(delibere_data)
        economicita = self._calcola_economicita(delibere_data)
        trasparenza = self._calcola_trasparenza(delibere_data)
        
        # Combina tutti i KPI in un unico dizionario
        dashboard_kpi = {
            'timestamp_elaborazione': datetime.now().isoformat(),
            'totale_documenti_analizzati': len(delibere_data),
            'periodo_analisi': self._determina_periodo_analisi(delibere_data),
            'efficienza': efficienza,
            'efficacia': efficacia,
            'economicita': economicita,
            'trasparenza': trasparenza,
            'kpi_aggregati': self._calcola_kpi_aggregati(efficienza, efficacia, economicita, trasparenza)
        }
        
        return dashboard_kpi
    
    def _determina_periodo_analisi(self, delibere_data: pd.DataFrame) -> Dict:
        """
        Determina il periodo coperto dall'analisi
        """
        periodo = {}
        if 'data_atto' in delibere_data.columns:
            delibere_data['data_atto'] = pd.to_datetime(
                delibere_data['data_atto'], 
                format='%d/%m/%Y', 
                errors='coerce'
            )
            valid_dates = delibere_data.dropna(subset=['data_atto'])
            if not valid_dates.empty:
                data_min = valid_dates['data_atto'].min()
                data_max = valid_dates['data_atto'].max()
                
                # Convert to strings for JSON serialization
                periodo['data_inizio'] = data_min.strftime('%d/%m/%Y') if pd.notna(data_min) else 'N/A'
                periodo['data_fine'] = data_max.strftime('%d/%m/%Y') if pd.notna(data_max) else 'N/A'
                
                # Calculate duration safely
                try:
                    duration = data_max - data_min
                    periodo['durata_giorni'] = duration.days if hasattr(duration, 'days') else 0
                except:
                    periodo['durata_giorni'] = 0  # Default to 0 if calculation fails
        
        return periodo
    
    def _calcola_kpi_aggregati(self, efficienza: Dict, efficacia: Dict, economicita: Dict, trasparenza: Dict) -> Dict:
        """
        Calcola KPI aggregati per una visione d'insieme
        """
        # Calcola punteggi composti per ogni dimensione (scala 0-100)
        score_efficienza = 50  # Punteggio base
        if 'tempo_medio_approvazione_gg' in efficienza:
            # Minore tempo è migliore (invertiamo la logica)
            tempo = efficienza['tempo_medio_approvazione_gg']
            if tempo > 0:
                score_efficienza = max(0, min(100, 100 - (tempo / 30) * 50))  # Penalizza oltre 30 giorni
        
        score_efficacia = 50
        if 'perc_documenti_classificati' in efficacia:
            score_efficacia = min(100, efficacia['perc_documenti_classificati'])
        
        score_economicita = 50
        if 'indice_concentrazione_hhi' in economicita:
            # HHI basso è migliore (meno concentrazione)
            hhi = economicita['indice_concentrazione_hhi']
            score_economicita = max(0, min(100, 100 - (hhi / 2500) * 50))  # Scala a 100 per HHI=0, 50 per HHI=2500
        
        score_trasparenza = 50
        if 'indice_completezza_%' in trasparenza:
            score_trasparenza = min(100, trasparenza['indice_completezza_%'])
        
        return {
            'score_efficienza_globale': round(score_efficienza, 2),
            'score_efficacia_globale': round(score_efficacia, 2),
            'score_economicita_globale': round(score_economicita, 2),
            'score_trasparenza_globale': round(score_trasparenza, 2),
            'score_globale_governance': round((score_efficienza + score_efficacia + score_economicita + score_trasparenza) / 4, 2)
        }
    
    def benchmark_analysis(self, current_data: pd.DataFrame, historical_data: pd.DataFrame = None) -> Dict:
        """
        Analisi benchmark:
        - Confronto con periodi precedenti
        - Trend analysis
        - Deviazioni significative
        """
        benchmark_results = {
            'current_period_kpi': self.generate_dashboard(current_data),
            'historical_comparison': {},
            'trend_analysis': {},
            'significant_deviations': []
        }
        
        if historical_data is not None and not historical_data.empty:
            # Calcola KPI per i dati storici
            historical_kpi = self.generate_dashboard(historical_data)
            benchmark_results['historical_kpi'] = historical_kpi
            
            # Confronto valori principali
            current_agg = benchmark_results['current_period_kpi']['kpi_aggregati']
            hist_agg = historical_kpi['kpi_aggregati']
            
            comparison = {}
            for kpi_name in ['score_efficienza_globale', 'score_efficacia_globale', 'score_economicita_globale', 'score_trasparenza_globale']:
                if kpi_name in current_agg and kpi_name in hist_agg:
                    current_val = current_agg[kpi_name]
                    hist_val = hist_agg[kpi_name]
                    change = ((current_val - hist_val) / hist_val * 100) if hist_val != 0 else 0
                    comparison[kpi_name] = {
                        'current_value': current_val,
                        'historical_value': hist_val,
                        'change_percentage': round(change, 2),
                        'trend': 'improvement' if change > 0 else 'decline' if change < 0 else 'stable'
                    }
            
            benchmark_results['historical_comparison'] = comparison
            
            # Identifica deviazioni significative
            for kpi_name, values in comparison.items():
                if abs(values['change_percentage']) > 10:  # Soglia del 10%
                    benchmark_results['significant_deviations'].append({
                        'kpi': kpi_name,
                        'description': f"{values['trend']} del {abs(values['change_percentage'])}% rispetto al periodo precedente",
                        'current_value': values['current_value'],
                        'historical_value': values['historical_value']
                    })
        
        return benchmark_results

def export_kpi_dashboard(kpi_results: Dict, output_dir: str = "data/avella/albo_download/report"):
    """
    Esporta il dashboard KPI
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Salva il report completo
    kpi_path = output_path / "kpi_dashboard.json"
    with open(kpi_path, 'w', encoding='utf-8') as f:
        json.dump(kpi_results, f, indent=2, ensure_ascii=False, default=str)
    
    logger.info(f"Dashboard KPI salvato in: {kpi_path}")
    
    # Crea un report sintetico in Excel
    excel_path = output_path / "kpi_dashboard.xlsx"
    
    with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
        # Foglio 1: KPI aggregati
        agg_data = []
        if 'kpi_aggregati' in kpi_results:
            for kpi, value in kpi_results['kpi_aggregati'].items():
                agg_data.append({'KPI': kpi, 'Valore': value})
        if agg_data:
            agg_df = pd.DataFrame(agg_data)
            agg_df.to_excel(writer, sheet_name='KPI_Aggregati', index=False)
        
        # Foglio 2: Efficienza
        if 'efficienza' in kpi_results:
            eff_data = []
            for kpi, value in kpi_results['efficienza'].items():
                eff_data.append({'KPI_Efficienza': kpi, 'Valore': value})
            if eff_data:
                eff_df = pd.DataFrame(eff_data)
                eff_df.to_excel(writer, sheet_name='Efficienza', index=False)
        
        # Foglio 3: Efficacia
        if 'efficacia' in kpi_results:
            eff_data = []
            for kpi, value in kpi_results['efficacia'].items():
                if isinstance(value, dict):
                    # Per distribuzioni, crea righe multiple
                    for sub_kpi, sub_value in value.items():
                        eff_data.append({'KPI_Efficacia': f"{kpi}_{sub_kpi}", 'Valore': sub_value})
                else:
                    eff_data.append({'KPI_Efficacia': kpi, 'Valore': value})
            if eff_data:
                eff_df = pd.DataFrame(eff_data)
                eff_df.to_excel(writer, sheet_name='Efficacia', index=False)
        
        # Foglio 4: Economicità
        if 'economicita' in kpi_results:
            eco_data = []
            for kpi, value in kpi_results['economicita'].items():
                if isinstance(value, dict):
                    # Per distribuzioni, crea righe multiple
                    for sub_kpi, sub_value in value.items():
                        eco_data.append({'KPI_Economicita': f"{kpi}_{sub_kpi}", 'Valore': sub_value})
                else:
                    eco_data.append({'KPI_Economicita': kpi, 'Valore': value})
            if eco_data:
                eco_df = pd.DataFrame(eco_data)
                eco_df.to_excel(writer, sheet_name='Economicita', index=False)
        
        # Foglio 5: Trasparenza
        if 'trasparenza' in kpi_results:
            transp_data = []
            for kpi, value in kpi_results['trasparenza'].items():
                transp_data.append({'KPI_Trasparenza': kpi, 'Valore': value})
            if transp_data:
                transp_df = pd.DataFrame(transp_data)
                transp_df.to_excel(writer, sheet_name='Trasparenza', index=False)
    
    logger.info(f"Dashboard KPI Excel salvato in: {excel_path}")
    
    # Crea report benchmark se presente
    if 'historical_comparison' in kpi_results:
        benchmark_path = output_path / "benchmark_storico.csv"
        comparison_data = []
        for kpi_name, values in kpi_results['historical_comparison'].items():
            comparison_data.append({
                'KPI': kpi_name,
                'Valore_Attuale': values['current_value'],
                'Valore_Storico': values['historical_value'],
                'Variazione_%': values['change_percentage'],
                'Trend': values['trend']
            })
        if comparison_data:
            benchmark_df = pd.DataFrame(comparison_data)
            benchmark_df.to_csv(benchmark_path, index=False)
            logger.info(f"Benchmark storico salvato in: {benchmark_path}")
    
    # Salva le deviazioni significative
    if 'significant_deviations' in kpi_results and kpi_results['significant_deviations']:
        anomalies_path = output_path / "anomalie_gestione.json"
        with open(anomalies_path, 'w', encoding='utf-8') as f:
            json.dump(kpi_results['significant_deviations'], f, indent=2, ensure_ascii=False, default=str)
        logger.info(f"Anomalie di gestione salvate in: {anomalies_path}")
    
    return kpi_path, excel_path

def run_management_kpi(input_path: str, output_dir: str = "data/avella/albo_download/report", historical_path: str = None):
    """
    Funzione principale per eseguire il calcolo dei KPI manageriali
    """
    logger.info(f"Caricamento dati da: {input_path}")
    
    # Carica i dati correnti
    df_current = pd.read_csv(input_path)
    logger.info(f"Dati correnti caricati: {len(df_current)} record")
    
    # Carica i dati storici se specificato
    df_historical = None
    if historical_path:
        logger.info(f"Caricamento dati storici da: {historical_path}")
        df_historical = pd.read_csv(historical_path)
        logger.info(f"Dati storici caricati: {len(df_historical)} record")
    
    # Crea il calcolatore KPI e genera il dashboard
    kpi_calculator = MunicipalManagementKPI()
    dashboard_results = kpi_calculator.generate_dashboard(df_current)
    
    # Esegui l'analisi benchmark se ci sono dati storici
    if df_historical is not None:
        benchmark_results = kpi_calculator.benchmark_analysis(df_current, df_historical)
        dashboard_results.update(benchmark_results)
    
    # Esporta i risultati
    export_kpi_dashboard(dashboard_results, output_dir)
    
    logger.info("Processo di calcolo KPI manageriali completato!")

def main():
    """
    Funzione principale per consentire l'esecuzione da riga di comando
    """
    parser = argparse.ArgumentParser(description='Genera KPI manageriali per controllo di gestione')
    parser.add_argument('--input', type=str, required=True, 
                       help='Percorso del file CSV di input contenente i dati delle delibere')
    parser.add_argument('--output-dir', type=str, default='data/avella/albo_download/report',
                       help='Directory di output per i risultati')
    parser.add_argument('--historical', type=str, default=None,
                       help='Percorso del file CSV di input contenente i dati storici per benchmark')
    
    args = parser.parse_args()
    
    run_management_kpi(args.input, args.output_dir, args.historical)

if __name__ == "__main__":
    main()