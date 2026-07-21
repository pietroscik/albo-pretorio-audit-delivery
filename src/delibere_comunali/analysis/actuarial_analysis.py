#!/usr/bin/env python3
"""
Actuarial Analysis Dashboard
Provides statistical analysis and risk modeling for municipal financial obligations
"""

import argparse
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from delibere_comunali.utils.config import get_tenant_dir


def calculate_actuarial_metrics(df: pd.DataFrame) -> Dict[str, float]:
    """Calculate key actuarial metrics for municipal financial analysis."""
    metrics = {}
    
    # Total financial exposure
    if 'importo_max' in df.columns and df['importo_max'].notna().any():
        importi = df['importo_max'].dropna()
        metrics['total_exposure'] = float(importi.sum())
        metrics['avg_obligation'] = float(importi.mean())
        metrics['std_obligation'] = float(importi.std())
        metrics['max_obligation'] = float(importi.max())
        metrics['min_obligation'] = float(importi.min())
        
        # Percentiles
        metrics['p25_obligation'] = float(importi.quantile(0.25))
        metrics['p50_obligation'] = float(importi.quantile(0.50))
        metrics['p75_obligation'] = float(importi.quantile(0.75))
        metrics['p95_obligation'] = float(importi.quantile(0.95))
    
    # Temporal distribution if dates available
    if 'data_atto' in df.columns:
        df_dates = df.dropna(subset=['data_atto'])
        if not df_dates.empty:
            df_dates['data_atto'] = pd.to_datetime(df_dates['data_atto'], errors='coerce')
            df_dates = df_dates.dropna(subset=['data_atto'])
            
            if not df_dates.empty:
                date_range = df_dates['data_atto'].max() - df_dates['data_atto'].min()
                metrics['observation_period_days'] = date_range.days
                metrics['num_documents_over_time'] = len(df_dates)
    
    return metrics


def main():
    parser = argparse.ArgumentParser(description="Actuarial Analysis Dashboard")
    parser.add_argument("--ente", required=True, help="Nome dell'ente locale da analizzare")
    args = parser.parse_args()
    
    ente = args.ente
    # get_tenant_dir already returns the full path including albo_download
    data_path = Path(get_tenant_dir(ente))
    # If the path already includes albo_download, don't add it again
    if not str(data_path).endswith("albo_download"):
        data_path = data_path / "albo_download"
    
    # Create Streamlit app
    st.set_page_config(page_title=f"Analisi Attuariale - {ente}", layout="wide")
    st.title(f"Dashboard Analisi Attuariale - {ente.upper()}")
    
    # Load data
    try:
        csv_path = data_path / "allegati_parsed.csv"
        if not csv_path.exists():
            st.error(f"File CSV non trovato: {csv_path}")
            st.stop()
        
        df = pd.read_csv(csv_path)
        st.success(f"Dati caricati: {len(df)} record da {ente}")
        
        # Calculate actuarial metrics
        metrics = calculate_actuarial_metrics(df)
        
        # Display key metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total_exp = metrics.get('total_exposure', 0)
            st.metric("Esposizione Totale", f"€ {total_exp:,.2f}", 
                     delta=None, help="Somma di tutti gli importi dichiarati")
        
        with col2:
            avg_obl = metrics.get('avg_obligation', 0)
            st.metric("Obbligo Medio", f"€ {avg_obl:,.2f}", 
                     delta=None, help="Media degli obblighi finanziari")
        
        with col3:
            p95_obl = metrics.get('p95_obligation', 0)
            st.metric("95° Percentile", f"€ {p95_obl:,.2f}", 
                     delta=None, help="Valore sotto cui cade il 95% degli obblighi")
        
        with col4:
            obs_period = metrics.get('observation_period_days', 0)
            st.metric("Periodo Osservato", f"{obs_period} giorni", 
                     delta=None, help="Arco temporale di osservazione")
        
        # Distribution analysis
        if 'importo_max' in df.columns and df['importo_max'].notna().any():
            st.subheader("Distribuzione degli Importi")
            
            # Histogram
            importi_clean = df['importo_max'].dropna()
            fig_hist = px.histogram(importi_clean, nbins=50, 
                                   title="Distribuzione degli Importi (istogramma)",
                                   labels={'value': 'Importo (€)', 'count': 'Frequenza'})
            st.plotly_chart(fig_hist, use_container_width=True)
            
            # Box plot
            fig_box = px.box(importi_clean, title="Box Plot degli Importi (scala logaritmica)", log_y=True)
            st.plotly_chart(fig_box, use_container_width=True)
            
            # Cumulative distribution
            importi_sorted = np.sort(importi_clean)
            cumulative_prob = np.arange(1, len(importi_sorted) + 1) / len(importi_sorted)
            
            fig_cum = go.Figure()
            fig_cum.add_trace(go.Scatter(x=importi_sorted, y=cumulative_prob, 
                                        mode='lines', name='CDF'))
            fig_cum.update_layout(title="Funzione di Distribuzione Cumulativa",
                                 xaxis_title="Importo (€)",
                                 yaxis_title="Probabilità Cumulativa")
            st.plotly_chart(fig_cum, use_container_width=True)
        
        # Risk analysis
        st.subheader("Analisi del Rischio")
        col1, col2 = st.columns(2)
        
        with col1:
            if 'importo_max' in df.columns and df['importo_max'].notna().any():
                importi = df['importo_max'].dropna()
                high_risk_threshold = metrics.get('p95_obligation', importi.quantile(0.95))
                high_risk_count = (importi > high_risk_threshold).sum()
                high_risk_pct = (high_risk_count / len(importi)) * 100
                
                st.write(f"Importi oltre il 95° percentile (€ {high_risk_threshold:,.2f}):")
                st.write(f"- Numero: {high_risk_count}")
                st.write(f"- Percentuale: {high_risk_pct:.2f}%")
                
                # Concentration risk
                top_10_pct_count = max(1, int(len(importi) * 0.10))
                top_10_pct_importi = importi.nlargest(top_10_pct_count)
                top_10_pct_value = top_10_pct_importi.sum()
                total_value = importi.sum()
                concentration_ratio = (top_10_pct_value / total_value) * 100
                
                st.write(f"Rischio di concentrazione (top 10%):")
                st.write(f"- Valore: € {top_10_pct_value:,.2f}")
                st.write(f"- Percentuale totale: {concentration_ratio:.2f}%")
        
        with col2:
            if 'data_atto' in df.columns:
                df_dates = df.dropna(subset=['data_atto'])
                if not df_dates.empty:
                    df_dates['data_atto'] = pd.to_datetime(df_dates['data_atto'], errors='coerce')
                    df_dates = df_dates.dropna(subset=['data_atto'])
                    
                    if not df_dates.empty:
                        monthly_agg = df_dates.groupby(df_dates['data_atto'].dt.to_period('M')).agg({
                            'importo_max': ['sum', 'mean', 'count']
                        }).round(2)
                        
                        monthly_agg.columns = ['importo_tot_mensile', 'importo_medio_mensile', 'conteggio_mensile']
                        monthly_agg = monthly_agg.reset_index()
                        monthly_agg['data_atto'] = monthly_agg['data_atto'].dt.to_timestamp()
                        
                        fig_monthly = px.line(monthly_agg, x='data_atto', y='importo_tot_mensile',
                                            title="Importi Totali Mensili")
                        st.plotly_chart(fig_monthly, use_container_width=True)
        
        # Detailed metrics table
        st.subheader("Metriche Dettagliate")
        st.json(metrics)
    
    except Exception as e:
        st.error(f"Errore durante l'analisi attuariale: {str(e)}")
        import traceback
        st.code(traceback.format_exc())


if __name__ == "__main__":
    main()