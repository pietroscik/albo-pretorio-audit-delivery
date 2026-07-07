#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Modulo di analisi attuariale per il sistema di audit dell'albo pretorio
Implementa calcoli attuariali per la stima degli impegni di spesa futuri
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import logging
from datetime import datetime
import json
from scipy import stats
from sklearn.linear_model import LinearRegression
from dateutil.relativedelta import relativedelta
import argparse

# Configura il logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ActuarialAnalyzer:
    """
    Classe per l'analisi attuariale degli impegni di spesa
    """
    
    def __init__(self):
        # Tassi di attualizzazione standard (da aggiornare secondo mercato)
        self.discount_rates = {
            '1_year': 0.02,   # 2% per 1 anno
            '3_years': 0.025, # 2.5% per 3 anni
            '5_years': 0.03,  # 3% per 5 anni
            '10_years': 0.035 # 3.5% per 10 anni
        }
        
        # Tabelle di mortalità/rottura per impegni (semplificate)
        self.commitment_mortality_table = {
            # Probabilità di rottura per durata dell'impegno
            '0-6_months': 0.05,
            '6-12_months': 0.08,
            '1-2_years': 0.12,
            '2-3_years': 0.15,
            '3-5_years': 0.18,
            '5+_years': 0.20
        }
    
    def _calculate_discount_factor(self, years: float, rate: float = None) -> float:
        """
        Calcola il fattore di attualizzazione
        """
        if rate is None:
            # Usa tasso appropriato in base alla durata
            if years <= 1:
                rate = self.discount_rates['1_year']
            elif years <= 3:
                rate = self.discount_rates['3_years']
            elif years <= 5:
                rate = self.discount_rates['5_years']
            else:
                rate = self.discount_rates['10_years']
        
        return 1 / ((1 + rate) ** years)
    
    def calculate_provisioning(self, impegni: pd.DataFrame) -> Dict:
        """
        Stima attuariale degli impegni futuri
        - Attualizzazione flussi di cassa
        - Calcolo riserve per impegni pluriennali
        - Stima probabilità di esecuzione
        """
        if impegni.empty:
            return {
                'total_provisioning': 0.0,
                'reserve_by_year': {},
                'confidence_interval': (0.0, 0.0),
                'break_probability': 0.0
            }
        
        # Calcola la data odierna per i calcoli temporali
        oggi = datetime.today()
        
        # Mappa le colonne disponibili a quelle utilizzate nel calcolo
        # Invece di 'data_impegno' e 'data_scadenza', useremo 'data_atto' e stimeremo la scadenza
        if 'data_atto' in impegni.columns:
            # Converti la data atto al formato corretto
            impegni['data_atto'] = pd.to_datetime(
                impegni['data_atto'], 
                format='%d/%m/%Y', 
                errors='coerce'
            )
            
            # Stima data di scadenza basata su data_atto + durata media (es. 1 anno)
            # Possiamo usare anche impegno_anno se disponibile
            if 'impegno_anno' in impegni.columns and 'impegno_num' in impegni.columns:
                # Se abbiamo numero e anno di impegno, possiamo fare stime migliori
                pass  # Per ora continuiamo con la stima semplice
            
            # Per ogni record, stima la data di scadenza come data_atto + 1 anno (ipotesi)
            # Oppure, se abbiamo informazioni su durata, usale
            data_impegno_col = 'data_atto'
            # Per la scadenza, useremo una stima basata sul tipo di impegno o una durata standard
            # In mancanza di informazioni precise, assumiamo 1 anno come default
            impegni['data_scadenza_stimata'] = impegni[data_impegno_col] + pd.DateOffset(years=1)
            
            # Rimuovi righe con date non valide
            impegni_valid = impegni.dropna(subset=[data_impegno_col, 'data_scadenza_stimata'])
        else:
            # Se non abbiamo la data_atto, usiamo una data fittizia
            logger.warning("Nessuna colonna data trovata, uso date fittizie")
            impegni_valid = impegni.copy()
            # Assegna una data fittizia per permettere i calcoli
            impegni_valid['data_atto'] = pd.to_datetime(datetime.today())
            impegni_valid['data_scadenza_stimata'] = pd.to_datetime(datetime.today() + relativedelta(years=1))
        
        total_provisioning = 0.0
        yearly_provisions = {}
        total_break_prob = 0.0
        
        for idx, row in impegni_valid.iterrows():
            importo = row.get('importo_max', 0.0)
            if pd.isna(importo) or importo <= 0:
                continue
            
            data_impegno = row.get('data_atto', oggi)
            data_scadenza = row.get('data_scadenza_stimata', oggi + relativedelta(years=1))
            
            # Calcola la durata in anni
            if pd.isna(data_impegno) or pd.isna(data_scadenza):
                continue
                
            durata_anni = (data_scadenza - data_impegno).days / 365.25
            
            # Calcola il fattore di attualizzazione
            discount_factor = self._calculate_discount_factor(durata_anni)
            
            # Calcola la probabilità di rottura in base alla durata
            if durata_anni <= 0.5:
                break_prob = self.commitment_mortality_table['0-6_months']
            elif durata_anni <= 1:
                break_prob = self.commitment_mortality_table['6-12_months']
            elif durata_anni <= 2:
                break_prob = self.commitment_mortality_table['1-2_years']
            elif durata_anni <= 3:
                break_prob = self.commitment_mortality_table['2-3_years']
            elif durata_anni <= 5:
                break_prob = self.commitment_mortality_table['3-5_years']
            else:
                break_prob = self.commitment_mortality_table['5+_years']
            
            # Calcola il valore atteso (valore attualizzato * probabilità di esecuzione)
            valore_previsto = importo * discount_factor * (1 - break_prob)
            
            # Somma al totale
            total_provisioning += valore_previsto
            total_break_prob += break_prob
            
            # Aggiungi al calcolo per anno
            anno_scadenza = data_scadenza.year
            if anno_scadenza not in yearly_provisions:
                yearly_provisions[anno_scadenza] = 0.0
            yearly_provisions[anno_scadenza] += valore_previsto
        
        # Calcola intervallo di confidenza (semplificato)
        n_impegni = len(impegni_valid)
        if n_impegni > 1:
            # Usa bootstrap semplificato per calcolare CI
            sample_means = []
            for _ in range(100):  # Bootstrap con 100 campioni
                sample = impegni_valid.sample(n=n_impegni, replace=True)
                sample_prov = 0.0
                for idx, row in sample.iterrows():
                    importo = row.get('importo_max', 0.0)
                    if pd.isna(importo) or importo <= 0:
                        continue
                    
                    data_impegno = row.get('data_atto', oggi)
                    data_scadenza = row.get('data_scadenza_stimata', oggi + relativedelta(years=1))
                    if pd.isna(data_impegno) or pd.isna(data_scadenza):
                        continue
                    
                    durata_anni = (data_scadenza - data_impegno).days / 365.25
                    discount_factor = self._calculate_discount_factor(durata_anni)
                    
                    if durata_anni <= 0.5:
                        break_prob = self.commitment_mortality_table['0-6_months']
                    elif durata_anni <= 1:
                        break_prob = self.commitment_mortality_table['6-12_months']
                    elif durata_anni <= 2:
                        break_prob = self.commitment_mortality_table['1-2_years']
                    elif durata_anni <= 3:
                        break_prob = self.commitment_mortality_table['2-3_years']
                    elif durata_anni <= 5:
                        break_prob = self.commitment_mortality_table['3-5_years']
                    else:
                        break_prob = self.commitment_mortality_table['5+_years']
                    
                    valore_previsto = importo * discount_factor * (1 - break_prob)
                    sample_prov += valore_previsto
                sample_means.append(sample_prov)
            
            # Calcola intervallo di confidenza al 95%
            ci_lower = np.percentile(sample_means, 2.5)
            ci_upper = np.percentile(sample_means, 97.5)
            confidence_interval = (ci_lower, ci_upper)
        else:
            confidence_interval = (total_provisioning * 0.8, total_provisioning * 1.2)
        
        return {
            'total_provisioning': round(total_provisioning, 2),
            'reserve_by_year': {str(k): round(v, 2) for k, v in yearly_provisions.items()},
            'confidence_interval': (round(confidence_interval[0], 2), round(confidence_interval[1], 2)),
            'break_probability_avg': round(total_break_prob / max(1, n_impegni), 4) if n_impegni > 0 else 0.0
        }
    
    def survival_analysis(self, procedures: pd.DataFrame) -> Dict:
        """
        Analisi di sopravvivenza delle procedure
        - Tempo medio completamento iter
        - Probabilità completamento entro deadline
        - Identificazione colli di bottiglia
        """
        if procedures.empty:
            return {
                'avg_completion_time': 0,
                'completion_probability': 0.0,
                'bottlenecks': [],
                'survival_curve': {}
            }
        
        # Invece di 'data_completamento', useremo 'data_registro' come proxy per il completamento
        # e 'data_atto' come inizio
        data_inizio_col = 'data_atto' if 'data_atto' in procedures.columns else None
        data_fine_col = 'data_registro' if 'data_registro' in procedures.columns else None
        
        if not data_inizio_col or not data_fine_col:
            # Se non abbiamo entrambe le date, usiamo solo data_atto con stime
            if 'data_atto' in procedures.columns:
                procedures['data_atto'] = pd.to_datetime(
                    procedures['data_atto'], 
                    format='%d/%m/%Y', 
                    errors='coerce'
                )
                # Per la sopravvivenza, considereremo solo la distribuzione temporale
                valid_dates = procedures.dropna(subset=['data_atto'])
                if not valid_dates.empty:
                    # Ordina per data e calcola alcune metriche temporali
                    valid_dates = valid_dates.sort_values('data_atto')
                    valid_dates['giorni_da_prima'] = (
                        valid_dates['data_atto'] - valid_dates['data_atto'].min()
                    ).dt.days
                    
                    avg_time = valid_dates['giorni_da_prima'].mean()
                    return {
                        'avg_completion_time': round(avg_time, 2),
                        'completion_probability': 1.0,  # Tutti completati (dati storici)
                        'bottlenecks': [],
                        'survival_curve': {},  # Da implementare in modo più significativo
                        'std_completion_time': round(valid_dates['giorni_da_prima'].std(), 2) if len(valid_dates) > 1 else 0
                    }
            return {
                'avg_completion_time': 0,
                'completion_probability': 0.0,
                'bottlenecks': [],
                'survival_curve': {},
                'std_completion_time': 0
            }
        
        # Assicurati che le date siano nel formato corretto
        procedures[data_inizio_col] = pd.to_datetime(
            procedures[data_inizio_col], 
            format='%d/%m/%Y', 
            errors='coerce'
        )
        
        procedures[data_fine_col] = pd.to_datetime(
            procedures[data_fine_col], 
            format='%d/%m/%Y', 
            errors='coerce'
        )
        
        # Calcola tempi di completamento
        procedures = procedures.copy()
        procedures['giorni_completamento'] = (
            procedures[data_fine_col] - procedures[data_inizio_col]
        ).dt.days
        
        # Filtra procedure con tempi di completamento validi
        proc_valid = procedures[
            (procedures['giorni_completamento'].notna()) & 
            (procedures['giorni_completamento'] >= 0)
        ].copy()
        
        if not proc_valid.empty:
            avg_completion_time = proc_valid['giorni_completamento'].mean()
            std_completion_time = proc_valid['giorni_completamento'].std()
        else:
            avg_completion_time = 0
            std_completion_time = 0
        
        # Stima probabilità di completamento (tutte le procedure nel dataset sono completate)
        total_proc = len(procedures)
        completed_proc = len(proc_valid)
        completion_probability = completed_proc / total_proc if total_proc > 0 else 0.0
        
        # Identifica possibili colli di bottiglia (procedure con tempi molto superiori alla media)
        bottlenecks = []
        if not proc_valid.empty and avg_completion_time > 0:
            threshold = avg_completion_time + (2 * std_completion_time) if std_completion_time > 0 else avg_completion_time * 2
            long_procedures = proc_valid[proc_valid['giorni_completamento'] > threshold]
            
            for idx, row in long_procedures.iterrows():
                bottlenecks.append({
                    'pdf_name': row.get('pdf_name', ''),
                    'category': row.get('category', ''),
                    'giorni_completamento': row['giorni_completamento'],
                    'descrizione': f"Procedure {row.get('category', 'N/A')} con tempo di completamento elevato ({row['giorni_completamento']} giorni)"
                })
        
        # Curve di sopravvivenza semplificata (probabilità di non essere completata entro un certo tempo)
        survival_curve = {}
        if not proc_valid.empty:
            giorni_unici = sorted(proc_valid['giorni_completamento'].unique())
            for giorni in giorni_unici:
                non_complete = len(proc_valid[proc_valid['giorni_completamento'] > giorni])
                survival_curve[int(giorni)] = non_complete / len(proc_valid)
        
        return {
            'avg_completion_time': round(avg_completion_time, 2) if pd.notna(avg_completion_time) else 0,
            'completion_probability': round(completion_probability, 4),
            'bottlenecks': bottlenecks,
            'survival_curve': survival_curve,
            'std_completion_time': round(std_completion_time, 2) if pd.notna(std_completion_time) else 0
        }
    
    def calculate_cash_flow_projection(self, impegni: pd.DataFrame, projection_years: int = 5) -> Dict:
        """
        Proiezione flussi di cassa attualizzati
        """
        oggi = datetime.today()
        cash_flows = {}
        
        # Mappa le colonne disponibili
        if 'data_atto' in impegni.columns:
            # Converti la data atto al formato corretto
            impegni['data_atto'] = pd.to_datetime(
                impegni['data_atto'], 
                format='%d/%m/%Y', 
                errors='coerce'
            )
            
            # Stima data di pagamento come data_atto + durata media
            # Per ora assumiamo che i pagamenti avvengano 1 anno dopo l'impegno
            impegni['data_pagamento_stimata'] = impegni['data_atto'] + pd.DateOffset(years=1)
            
            impegni_valid = impegni.dropna(subset=['data_pagamento_stimata', 'importo_max'])
        else:
            # Se non abbiamo date, usiamo date fittizie
            logger.warning("Nessuna colonna data trovata per proiezione cassa, uso date fittizie")
            impegni_valid = impegni.copy()
            impegni_valid['data_pagamento_stimata'] = pd.to_datetime(oggi + relativedelta(years=1))
        
        for year_offset in range(1, projection_years + 1):
            target_date = oggi + relativedelta(years=year_offset)
            target_year = target_date.year
            
            # Filtra impegni che hanno data di pagamento stimata in questo anno
            year_impegni = impegni_valid[
                (impegni_valid['data_pagamento_stimata'].dt.year == target_year)
            ].copy()
            
            if not year_impegni.empty:
                importo_totale = year_impegni['importo_max'].sum()
                
                # Calcola il valore attualizzato
                years_to_target = year_offset
                discount_factor = self._calculate_discount_factor(years_to_target)
                discounted_value = importo_totale * discount_factor
                
                cash_flows[str(target_year)] = {
                    'importo_nominale': round(importo_totale, 2),
                    'valore_attualizzato': round(discounted_value, 2),
                    'numero_impegni': len(year_impegni)
                }
            else:
                cash_flows[str(target_year)] = {
                    'importo_nominale': 0.0,
                    'valore_attualizzato': 0.0,
                    'numero_impegni': 0
                }
        
        return cash_flows

def export_actuarial_report(analyzer: ActuarialAnalyzer, df_impegni: pd.DataFrame, output_dir: str = "data/avella/albo_download/report"):
    """
    Esporta il report di analisi attuariale
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Calcola tutte le analisi
    provisioning_results = analyzer.calculate_provisioning(df_impegni)
    survival_results = analyzer.survival_analysis(df_impegni)
    cash_flow_projection = analyzer.calculate_cash_flow_projection(df_impegni)
    
    # Salva il report principale di provisioning
    provisioning_path = output_path / "provisioning_attuariale.xlsx"
    
    with pd.ExcelWriter(provisioning_path, engine='openpyxl') as writer:
        # Foglio 1: Provisioning generale
        prov_df = pd.DataFrame([provisioning_results])
        prov_df.to_excel(writer, sheet_name='Provisioning_Generale', index=False)
        
        # Foglio 2: Riserve per anno
        if provisioning_results['reserve_by_year']:
            yearly_df = pd.DataFrame(
                list(provisioning_results['reserve_by_year'].items()),
                columns=['Anno', 'Riserva_Attualizzata']
            )
            yearly_df.to_excel(writer, sheet_name='Riserve_Per_Anno', index=False)
        
        # Foglio 3: Proiezione flussi di cassa
        if cash_flow_projection:
            cf_data = []
            for year, data in cash_flow_projection.items():
                cf_data.append({
                    'Anno': year,
                    'Importo_Nominale': data['importo_nominale'],
                    'Valore_Attualizzato': data['valore_attualizzato'],
                    'Numero_Impegni': data['numero_impegni']
                })
            cf_df = pd.DataFrame(cf_data)
            cf_df.to_excel(writer, sheet_name='Flussi_Cassa_Proiezione', index=False)
    
    logger.info(f"Report provisioning attuariale salvato in: {provisioning_path}")
    
    # Salva analisi di sopravvivenza
    survival_path = output_path / "sopravvivenza_procedure.json"
    with open(survival_path, 'w', encoding='utf-8') as f:
        json.dump(survival_results, f, indent=2, ensure_ascii=False, default=str)
    
    logger.info(f"Analisi sopravvivenza procedure salvata in: {survival_path}")
    
    # Salva proiezioni flussi di cassa
    cash_flow_path = output_path / "cash_flow_projections.csv"
    cf_data = []
    for year, data in cash_flow_projection.items():
        cf_data.append({
            'Anno': year,
            'Importo_Nominale': data['importo_nominale'],
            'Valore_Attualizzato': data['valore_attualizzato'],
            'Numero_Impegni': data['numero_impegni']
        })
    cf_df = pd.DataFrame(cf_data)
    cf_df.to_csv(cash_flow_path, index=False)
    
    logger.info(f"Proiezioni flussi di cassa salvate in: {cash_flow_path}")
    
    return provisioning_path, survival_path, cash_flow_path

def run_actuarial_analysis(input_path: str, output_dir: str = "data/avella/albo_download/report"):
    """
    Funzione principale per eseguire l'analisi attuariale
    """
    logger.info(f"Caricamento dati da: {input_path}")
    
    # Carica i dati
    df = pd.read_csv(input_path)
    logger.info(f"Dati caricati: {len(df)} record")
    
    # Crea l'analizzatore e calcola le metriche
    analyzer = ActuarialAnalyzer()
    
    # Esporta i risultati
    export_actuarial_report(analyzer, df, output_dir)
    
    logger.info("Processo di analisi attuariale completato!")

def main():
    """
    Funzione principale per consentire l'esecuzione da riga di comando
    """
    parser = argparse.ArgumentParser(description='Analisi attuariale impegni di spesa')
    parser.add_argument('--input', type=str, required=True, 
                       help='Percorso del file CSV di input contenente i dati degli impegni')
    parser.add_argument('--output-dir', type=str, default='data/avella/albo_download/report',
                       help='Directory di output per i risultati')
    
    args = parser.parse_args()
    
    run_actuarial_analysis(args.input, args.output_dir)

if __name__ == "__main__":
    main()