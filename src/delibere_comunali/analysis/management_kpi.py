#!/usr/bin/env python3
"""
Management KPI Analysis Dashboard
Visualizes key performance indicators for municipal administration efficiency
"""

import argparse
import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path
import sys
from typing import Dict, Any

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from delibere_comunali.management_kpi.kpi_calculator import MunicipalManagementKPI
from delibere_comunali.utils.config import get_tenant_dir


def main():
    parser = argparse.ArgumentParser(description="Management KPI Analysis")
    parser.add_argument("--ente", required=True, help="Nome dell'ente locale da analizzare")
    args = parser.parse_args()
    
    ente = args.ente
    # get_tenant_dir already returns the full path including albo_download
    data_path = Path(get_tenant_dir(ente))
    # If the path already includes albo_download, don't add it again
    if not str(data_path).endswith("albo_download"):
        data_path = data_path / "albo_download"
    
    # Create Streamlit app
    st.set_page_config(page_title=f"KPI Management - {ente}", layout="wide")
    st.title(f"KPI Management Dashboard - {ente.upper()}")
    
    # Load data
    try:
        csv_path = data_path / "allegati_parsed.csv"
        if not csv_path.exists():
            st.error(f"File CSV non trovato: {csv_path}")
            st.stop()
        
        df = pd.read_csv(csv_path)
        st.success(f"Dati caricati: {len(df)} record da {ente}")
        
        # Calculate KPIs using the correct class
        calculator = MunicipalManagementKPI()
        kpis = calculator.generate_dashboard(df)
        
        # Display KPIs in columns
        col1, col2, col3, col4 = st.columns(4)
        
        # Extract KPI values from the nested dictionary structure
        trasparenza = kpis.get('trasparenza', {})
        if trasparenza:
            with col1:
                completezza = trasparenza.get('indice_completezza_%', 0)
                st.metric("Completezza Media", f"{completezza}%", 
                         delta=None, help="Percentuale media di campi compilati")
        
            with col2:
                perc_cig = trasparenza.get('perc_documenti_con_cig_%', 0)
                st.metric("Documenti con CIG", f"{perc_cig}%", 
                         delta=None, help="Percentuale di documenti con codice CIG")
        
            with col3:
                perc_cup = trasparenza.get('perc_documenti_con_cup_%', 0)
                st.metric("Documenti con CUP", f"{perc_cup}%", 
                         delta=None, help="Percentuale di documenti con codice CUP")
        
            with col4:
                # Look for text validity metric
                text_validity_key = next((key for key in trasparenza.keys() if 'testo' in key and 'valid' in key), None)
                text_validity = trasparenza.get(text_validity_key, 0) if text_validity_key else 0
                st.metric("Testo Valido", f"{text_validity}%", 
                         delta=None, help="Documenti con testo sufficientemente lungo")
        
        # Show detailed KPI breakdown
        st.subheader("Dettaglio KPI")
        st.json(kpis)
        
        # Visualize some key metrics
        if 'importo_max' in df.columns and df['importo_max'].notna().any():
            st.subheader("Distribuzione Importi per Categoria")
            fig = px.box(df.dropna(subset=['importo_max']), x='category', y='importo_max',
                        title="Box Plot Importi per Categoria", log_y=True)
            st.plotly_chart(fig, use_container_width=True)
        
        # Timeline visualization if dates are available
        if 'data_atto' in df.columns and pd.to_datetime(df['data_atto'], errors='coerce').notna().any():
            df_temporal = df.copy()
            df_temporal['data_atto'] = pd.to_datetime(df_temporal['data_atto'], errors='coerce')
            df_temporal = df_temporal.dropna(subset=['data_atto'])
            
            if not df_temporal.empty:
                st.subheader("Timeline Documenti per Categoria")
                df_timeline = df_temporal.groupby([df_temporal['data_atto'].dt.to_period('M'), 'category']).size().reset_index(name='count')
                df_timeline['data_atto'] = df_timeline['data_atto'].dt.to_timestamp()
                fig2 = px.line(df_timeline, x='data_atto', y='count', color='category',
                              title="Numero di Documenti per Mese e Categoria")
                st.plotly_chart(fig2, use_container_width=True)
    
    except Exception as e:
        st.error(f"Errore durante l'analisi: {str(e)}")
        import traceback
        st.code(traceback.format_exc())


if __name__ == "__main__":
    main()