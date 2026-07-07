#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Modulo di Risk Assessment per il sistema di audit dell'albo pretorio
Implementa valutazione del rischio per le delibere e determinazioni
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import logging
from datetime import datetime
import json
import argparse
from dateutil.relativedelta import relativedelta

# Configura il logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DeliberaRiskAssessor:
    """
    Classe per la valutazione del rischio associato alle delibere e determinazioni
    """
    
    def __init__(self):
        self.risk_weights = {
            'importo': 0.30,      # Peso per l'importo dell'atto
            'urgenza': 0.15,      # Peso per l'urgenza/procedura accelerata
            'contraente': 0.20,   # Peso per la ricorrenza del fornitore
            'normativa': 0.15,    # Peso per la compliance normativa
            'temporal': 0.10,     # Peso per aspetti temporali
            'settore': 0.10       # Peso per il settore di intervento
        }
        
        # Soglie per la categorizzazione del rischio
        self.risk_thresholds = {
            'basso': (0, 30),
            'medio': (31, 60),
            'alto': (61, 80),
            'molto_alto': (81, 100)
        }
    
    def _safe_str(self, value) -> str:
        """
        Converte un valore in stringa in modo sicuro, gestendo None e NaN
        """
        if pd.isna(value) or value is None:
            return ''
        return str(value)
    
    def _safe_float(self, value) -> float:
        """
        Converte un valore in float in modo sicuro, gestendo None e valori non numerici
        """
        if pd.isna(value) or value is None:
            return 0.0
        try:
            return float(value) if value != '' else 0.0
        except (ValueError, TypeError):
            return 0.0
    
    def _calcola_rischio_importo(self, importo: float, importo_medio_settore: float = None) -> float:
        """
        Calcola il rischio basato sull'importo dell'atto
        """
        importo = self._safe_float(importo)
        if pd.isna(importo) or importo <= 0:
            return 0.0
        
        # Normalizzazione rispetto a un tetto massimo ragionevole
        tetto_massimo = 1_000_000  # 1 milione di euro come riferimento
        rischio_base = min(importo / tetto_massimo, 1.0) * 100
        
        # Se disponibile, confronta con la media del settore
        if importo_medio_settore and importo_medio_settore > 0:
            rapporto_media = importo / importo_medio_settore
            if rapporto_media > 2.0:  # Importo molto superiore alla media
                rischio_base *= 1.5
            elif rapporto_media > 1.5:  # Importo superiore alla media
                rischio_base *= 1.2
        
        return min(rischio_base, 100.0)
    
    def _valuta_procedura_urgenza(self, tipo_procedura: str, data_scadenza: str = None) -> float:
        """
        Valuta il rischio legato all'urgenza della procedura
        """
        tipo_procedura = self._safe_str(tipo_procedura)
        if not tipo_procedura:
            return 0.0
        
        # Identifica procedure urgenti
        termini_urgent = [
            'urgenza', 'emergenza', 'sotto soglia', 'affidamento diretto',
            'somma urgenza', 'deroga', 'accelerata'
        ]
        
        tipo_lower = tipo_procedura.lower()
        rischio = 0.0
        
        for termine in termini_urgent:
            if termine in tipo_lower:
                rischio = 70.0  # Alto rischio per procedure urgenti
                break
        
        # Se specificata una data di scadenza ravvicinata
        data_scadenza = self._safe_str(data_scadenza)
        if data_scadenza and data_scadenza.lower() != 'nan':
            try:
                data_scad = pd.to_datetime(data_scadenza)
                oggi = datetime.today()
                giorni_rimanenti = (data_scad - oggi).days
                
                if giorni_rimanenti <= 7:  # Settimana prossima
                    rischio += 15.0
                elif giorni_rimanenti <= 15:  # Due settimane
                    rischio += 10.0
            except:
                pass  # Ignora errori di parsing data
        
        return min(rischio, 100.0)
    
    def _verifica_ricorrenza_fornitore(self, fornitore: str, df_completo: pd.DataFrame) -> float:
        """
        Verifica la ricorrenza del fornitore negli atti recenti
        """
        fornitore = self._safe_str(fornitore)
        if not fornitore or fornitore.lower() in ['nan', '']:
            return 0.0
        
        # Conta quante volte compare il fornitore negli ultimi 6 mesi
        if 'data_atto' in df_completo.columns:
            df_recente = df_completo.copy()
            df_recente['data_atto'] = pd.to_datetime(df_recente['data_atto'], format='%d/%m/%Y', errors='coerce')
            sei_mesi_fa = datetime.now() - pd.DateOffset(months=6)
            df_recente = df_recente[df_recente['data_atto'] >= sei_mesi_fa]
        else:
            df_recente = df_completo
        
        # Conta occorrenze del fornitore
        conteggio_fornitore = len(df_recente[df_recente['beneficiario'].astype(str).str.contains(fornitore, case=False, na=False)])
        
        # Calcola rischio in base alla concentrazione
        if conteggio_fornitore >= 5:
            return 80.0  # Molto alto rischio di concentrazione
        elif conteggio_fornitore >= 3:
            return 60.0  # Alto rischio
        elif conteggio_fornitore >= 2:
            return 40.0  # Medio rischio
        else:
            return 0.0   # Basso rischio
    
    def _check_compliance_normativa(self, settore: str, tipo_atto: str) -> float:
        """
        Verifica la compliance normativa basata su settore e tipo atto
        """
        settore = self._safe_str(settore)
        tipo_atto = self._safe_str(tipo_atto)
        if not settore or not tipo_atto:
            return 0.0
        
        # Identifica settori ad alto rischio normativo
        settori_alto_rischio = [
            'lavori pubblici', 'appalti', 'procedura competitiva', 
            'affidamento', 'spesa contabile', 'bilancio'
        ]
        
        tipo_atto_alto_rischio = [
            'determinazione', 'atto contabile', 'aggiudicazione',
            'affidamento diretto', 'integrazione'
        ]
        
        rischio = 0.0
        
        settore_lower = settore.lower()
        tipo_lower = tipo_atto.lower()
        
        # Rischio per settore
        for sett in settori_alto_rischio:
            if sett in settore_lower:
                rischio += 20.0
                break
        
        # Rischio per tipo atto
        for tipo in tipo_atto_alto_rischio:
            if tipo in tipo_lower:
                rischio += 15.0
                break
        
        return min(rischio, 100.0)
    
    def _calcola_rischio_temporale(self, data_atto: str) -> float:
        """
        Calcola il rischio legato agli aspetti temporali
        """
        data_atto = self._safe_str(data_atto)
        if not data_atto or data_atto.lower() == 'nan':
            return 0.0
        
        try:
            data_doc = pd.to_datetime(data_atto, format='%d/%m/%Y', errors='coerce')
            if pd.isna(data_doc):
                return 0.0
                
            oggi = datetime.today()
            diff_giorni = abs((oggi - data_doc).days)
            
            # Rischio alto per documenti molto recenti (potrebbero essere non consolidati)
            if diff_giorni <= 7:  # Documento di questa settimana
                return 30.0
            elif diff_giorni <= 30:  # Documento di questo mese
                return 15.0
            else:
                return 0.0
        except:
            return 0.0
    
    def _calcola_rischio_settore(self, settore: str) -> float:
        """
        Calcola il rischio legato al settore di intervento
        """
        settore = self._safe_str(settore)
        if not settore:
            return 0.0
        
        # Settori ad alto rischio
        settori_alto_rischio = [
            'lavori pubblici', 'appalti', 'contratti pubblici', 'spesa contabile',
            'procedura competitiva', 'affidamento', 'manutenzione', 'servizi tecnici'
        ]
        
        # Settori a basso rischio
        settori_basso_rischio = [
            'personale', 'affari generali', 'pubblicazioni', 'contenzioso'
        ]
        
        settore_lower = settore.lower()
        
        for sett in settori_alto_rischio:
            if sett in settore_lower:
                return 60.0
        
        for sett in settori_basso_rischio:
            if sett in settore_lower:
                return 10.0
        
        return 30.0  # Rischio medio per default
    
    def _weighted_risk_calculation(self, delibera_data: Dict, df_completo: pd.DataFrame = None) -> float:
        """
        Calcola lo score di rischio complessivo con pesi specifici
        """
        # Estrai i valori dai dati della delibera usando metodi sicuri
        importo = self._safe_float(delibera_data.get('importo_max', 0.0))
        tipo_procedura = self._safe_str(delibera_data.get('tipo_procedura', ''))
        fornitore = self._safe_str(delibera_data.get('beneficiario', ''))
        settore = self._safe_str(delibera_data.get('category', ''))
        tipo_atto = self._safe_str(delibera_data.get('doc_type', ''))
        data_atto = self._safe_str(delibera_data.get('data_atto', ''))
        data_scadenza = self._safe_str(delibera_data.get('data_scadenza', ''))
        
        # Calcola i singoli fattori di rischio
        rischio_importo = self._calcola_rischio_importo(importo)
        rischio_urgenza = self._valuta_procedura_urgenza(tipo_procedura, data_scadenza)
        rischio_fornitore = self._verifica_ricorrenza_fornitore(fornitore, df_completo) if df_completo is not None else 0.0
        rischio_normativa = self._check_compliance_normativa(settore, tipo_atto)
        rischio_temporale = self._calcola_rischio_temporale(data_atto)
        rischio_settore = self._calcola_rischio_settore(settore)
        
        # Calcola il rischio complessivo pesato
        rischio_totale = (
            rischio_importo * self.risk_weights['importo'] +
            rischio_urgenza * self.risk_weights['urgenza'] +
            rischio_fornitore * self.risk_weights['contraente'] +
            rischio_normativa * self.risk_weights['normativa'] +
            rischio_temporale * self.risk_weights['temporal'] +
            rischio_settore * self.risk_weights['settore']
        )
        
        return min(rischio_totale, 100.0)
    
    def _categorize_risk(self, risk_score: float) -> str:
        """
        Categorizza il livello di rischio in base allo score
        """
        for category, (min_val, max_val) in self.risk_thresholds.items():
            if min_val <= risk_score <= max_val:
                return category
        return 'molto_alto'  # Per score > 80
    
    def _extract_factors(self, delibera_data: Dict) -> List[str]:
        """
        Estrae i fattori di rischio principali per la delibera
        """
        factors = []
        
        importo = self._safe_float(delibera_data.get('importo_max', 0.0))
        tipo_procedura = self._safe_str(delibera_data.get('tipo_procedura', ''))
        fornitore = self._safe_str(delibera_data.get('beneficiario', ''))
        settore = self._safe_str(delibera_data.get('category', ''))
        tipo_atto = self._safe_str(delibera_data.get('doc_type', ''))
        
        if importo > 100000:  # Importo elevato
            factors.append(f"Importo elevato: €{importo:,.2f}")
        
        if tipo_procedura and any(term in tipo_procedura.lower() for term in ['urgenza', 'emergenza', 'sotto soglia', 'affidamento diretto']):
            factors.append(f"Procedura urgente: {tipo_procedura}")
        
        if fornitore and fornitore.lower() not in ['diversi/nan', 'non identificato', 'non applicabile', 'nan', '']:
            factors.append(f"Fornitore: {fornitore}")
        
        if settore and any(s in settore.lower() for s in ['lavori pubblici', 'appalti', 'contratti']):
            factors.append(f"Settore ad alto rischio: {settore}")
        
        if tipo_atto and any(t in tipo_atto.lower() for t in ['determinazione', 'atto contabile']):
            factors.append(f"Tipo atto: {tipo_atto}")
        
        return factors if factors else ["Nessun fattore di rischio specifico identificato"]
    
    def _generate_recommendation(self, risk_score: float) -> str:
        """
        Genera una raccomandazione basata sul livello di rischio
        """
        if risk_score <= 30:
            return "Approvazione standard - Monitoraggio normale"
        elif risk_score <= 60:
            return "Richiede verifica supplementare - Richiesta documentazione aggiuntiva"
        elif risk_score <= 80:
            return "Alto rischio - Richiede approvazione superiore - Verifica approfondita"
        else:
            return "Rischio molto alto - Richiede commissione speciale - Blocco procedura fino a verifica"
    
    def assess_risk(self, delibera_data: Dict, df_completo: pd.DataFrame = None) -> Dict:
        """
        Calcola score di rischio 0-100 per ogni delibera
        Basato su: importo, procedura, fornitore, settore
        """
        risk_score = self._weighted_risk_calculation(delibera_data, df_completo)
        
        return {
            'risk_score': round(risk_score, 2),
            'risk_level': self._categorize_risk(risk_score),
            'risk_factors': self._extract_factors(delibera_data),
            'recommendation': self._generate_recommendation(risk_score)
        }
    
    def assess_all_delibere(self, df_delibere: pd.DataFrame) -> pd.DataFrame:
        """
        Valuta il rischio per tutte le delibere nel DataFrame
        """
        logger.info(f"Inizio valutazione rischio per {len(df_delibere)} delibere")
        
        results = []
        for idx, row in df_delibere.iterrows():
            delibera_dict = row.to_dict()
            risk_result = self.assess_risk(delibera_dict, df_delibere)
            
            # Aggiungi i risultati al dizionario
            delibera_dict.update({
                'risk_score': risk_result['risk_score'],
                'risk_level': risk_result['risk_level'],
                'risk_factors': '|'.join(risk_result['risk_factors']),
                'risk_recommendation': risk_result['recommendation']
            })
            
            results.append(delibera_dict)
            
            if idx % 100 == 0:  # Log progresso
                logger.info(f"Valutate {idx+1}/{len(df_delibere)} delibere...")
        
        logger.info("Valutazione rischio completata")
        return pd.DataFrame(results)

def export_risk_report(results_df: pd.DataFrame, output_dir: str = "data/avella/albo_download/report"):
    """
    Esporta il report di risk assessment
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Salva il report principale
    risk_report_path = output_path / "risk_assessment.csv"
    results_df.to_csv(risk_report_path, index=False)
    logger.info(f"Report risk assessment salvato in: {risk_report_path}")
    
    # Genera statistiche riassuntive
    stats = {
        'total_delibere': len(results_df),
        'avg_risk_score': round(results_df['risk_score'].mean(), 2),
        'high_risk_count': len(results_df[results_df['risk_score'] > 70]),
        'risk_distribution': results_df['risk_level'].value_counts().to_dict()
    }
    
    stats_path = output_path / "risk_statistics.json"
    with open(stats_path, 'w', encoding='utf-8') as f:
        json.dump(stats, f, indent=2, ensure_ascii=False, default=str)
    
    logger.info(f"Statistiche risk assessment salvate in: {stats_path}")
    
    # Salva la lista delle delibere ad alto rischio
    high_risk = results_df[results_df['risk_score'] > 70].copy()
    if not high_risk.empty:
        high_risk_path = output_path / "high_risk_delibere.json"
        high_risk_dict = high_risk[['pdf_name', 'risk_score', 'risk_level', 'risk_factors', 'risk_recommendation']].to_dict('records')
        with open(high_risk_path, 'w', encoding='utf-8') as f:
            json.dump(high_risk_dict, f, indent=2, ensure_ascii=False, default=str)
        
        logger.info(f"Lista delibere ad alto rischio salvata in: {high_risk_path}")
    
    return risk_report_path, stats_path

def run_risk_assessment(input_path: str, output_dir: str = "data/avella/albo_download/report"):
    """
    Funzione principale per eseguire la valutazione del rischio
    """
    logger.info(f"Caricamento dati da: {input_path}")
    
    # Carica i dati
    df = pd.read_csv(input_path)
    logger.info(f"Dati caricati: {len(df)} record")
    
    # Crea l'assessore e valuta il rischio
    assessor = DeliberaRiskAssessor()
    results_df = assessor.assess_all_delibere(df)
    
    # Esporta i risultati
    export_risk_report(results_df, output_dir)
    
    logger.info("Processo di risk assessment completato!")

def main():
    """
    Funzione principale per consentire l'esecuzione da riga di comando
    """
    parser = argparse.ArgumentParser(description='Valutazione rischi delibere')
    parser.add_argument('--input', type=str, required=True, 
                       help='Percorso del file CSV di input contenente i dati delle delibere')
    parser.add_argument('--output-dir', type=str, default='data/avella/albo_download/report',
                       help='Directory di output per i risultati')
    
    args = parser.parse_args()
    
    run_risk_assessment(args.input, args.output_dir)

if __name__ == "__main__":
    main()