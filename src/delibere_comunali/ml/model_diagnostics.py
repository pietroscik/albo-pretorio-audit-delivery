#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Modulo di diagnostica statistica avanzata per i modelli ML
Implementa tecniche statistiche avanzate per la valutazione e ottimizzazione dei modelli
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
from sklearn.model_selection import cross_val_score, StratifiedKFold
from sklearn.metrics import classification_report, confusion_matrix, roc_curve, auc
from sklearn.linear_model import LogisticRegression
from sklearn.feature_selection import SelectFromModel, RFE
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

# Configura il logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class StatisticalModelDiagnostics:
    """
    Classe per la diagnostica statistica avanzata dei modelli ML
    """
    
    def __init__(self):
        self.diagnostics_results = {}
        
    def calculate_aic_bic(self, model, X, y) -> Dict:
        """
        Calcola AIC e BIC per il modello
        """
        try:
            # Predizioni del modello
            y_pred_proba = model.predict_proba(X)
            
            # Calcola la log-likelihood
            n = len(y)
            k = len(model.coef_.flatten()) if hasattr(model, 'coef_') else X.shape[1]  # Numero di parametri
            
            # Per modelli probabilistici
            log_likelihood = np.sum(np.log(y_pred_proba[np.arange(len(y)), y]))
            
            # Calcola AIC e BIC
            aic = 2 * k - 2 * log_likelihood
            bic = n * np.log(-2 * log_likelihood / n) + k * np.log(n)
            
            return {
                'aic': aic,
                'bic': bic,
                'log_likelihood': log_likelihood,
                'params_count': k,
                'sample_size': n
            }
        except:
            # Se non è possibile calcolare AIC/BIC per il modello specifico
            return {
                'aic': np.nan,
                'bic': np.nan,
                'log_likelihood': np.nan,
                'params_count': np.nan,
                'sample_size': len(y)
            }
    
    def calculate_vif(self, X: pd.DataFrame) -> Dict:
        """
        Calcola il Variance Inflation Factor (VIF) per le features
        """
        try:
            from statsmodels.stats.outliers_influence import variance_inflation_factor
            
            # Assicurati che X sia un DataFrame
            if not isinstance(X, pd.DataFrame):
                X = pd.DataFrame(X)
            
            # Calcola VIF per ogni feature
            vif_data = []
            for i in range(X.shape[1]):
                vif = variance_inflation_factor(X.values, i)
                vif_data.append({
                    'feature': X.columns[i] if hasattr(X, 'columns') else f'feature_{i}',
                    'vif': vif
                })
            
            return pd.DataFrame(vif_data).to_dict('records')
        except ImportError:
            logger.warning("statsmodels non disponibile, impossibile calcolare VIF")
            return []
        except:
            logger.warning("Errore nel calcolo del VIF")
            return []
    
    def model_residual_analysis(self, model, X, y_true, y_pred) -> Dict:
        """
        Analisi dei residui del modello
        """
        residuals = y_true - y_pred
        
        # Test di normalità dei residui
        shapiro_stat, shapiro_p = stats.shapiro(residuals) if len(residuals) > 3 and len(residuals) <= 5000 else (np.nan, np.nan)
        
        # Statistiche descrittive dei residui
        residual_stats = {
            'mean': np.mean(residuals),
            'std': np.std(residuals),
            'median': np.median(residuals),
            'skewness': stats.skew(residuals),
            'kurtosis': stats.kurtosis(residuals),
            'shapiro_statistic': shapiro_stat,
            'shapiro_p_value': shapiro_p,
            'normality_test': 'Normal' if shapiro_p > 0.05 else 'Not Normal' if not np.isnan(shapiro_p) else 'N/A'
        }
        
        return residual_stats
    
    def calculate_roc_auc(self, model, X, y) -> Dict:
        """
        Calcola ROC e AUC per modelli classificatori
        """
        try:
            # Predizioni probabilistiche
            if hasattr(model, 'predict_proba'):
                y_pred_proba = model.predict_proba(X)
                
                # Se è un problema multiclasse, calcola macro-average
                if y_pred_proba.shape[1] > 2:
                    # Calcola ROC per ogni classe
                    fpr = {}
                    tpr = {}
                    roc_auc = {}
                    
                    for i in range(y_pred_proba.shape[1]):
                        fpr[i], tpr[i], _ = roc_curve(y, y_pred_proba[:, i], pos_label=i)
                        roc_auc[i] = auc(fpr[i], tpr[i])
                    
                    # Macro average
                    mean_auc = np.mean(list(roc_auc.values()))
                    
                    return {
                        'fpr': fpr,
                        'tpr': tpr,
                        'roc_auc': roc_auc,
                        'mean_auc': mean_auc,
                        'is_multiclass': True
                    }
                else:
                    # Problema binario
                    y_pred_proba_binary = y_pred_proba[:, 1]  # Probabilità classe positiva
                    fpr, tpr, thresholds = roc_curve(y, y_pred_proba_binary)
                    roc_auc_value = auc(fpr, tpr)
                    
                    return {
                        'fpr': fpr,
                        'tpr': tpr,
                        'roc_auc': roc_auc_value,
                        'thresholds': thresholds,
                        'is_multiclass': False
                    }
            else:
                return {
                    'error': 'Model does not support probability prediction'
                }
        except Exception as e:
            logger.warning(f"Errore nel calcolo di ROC/AUC: {str(e)}")
            return {
                'error': str(e)
            }
    
    def feature_importance_analysis(self, model, feature_names: List[str]) -> Dict:
        """
        Analisi dell'importanza delle features
        """
        importance_data = {}
        
        # Prova diversi metodi per ottenere l'importanza
        if hasattr(model, 'feature_importances_'):
            # Modelli ad albero
            importances = model.feature_importances_
            indices = np.argsort(importances)[::-1]
            
            importance_data = {
                'method': 'feature_importances_',
                'features': [feature_names[i] for i in indices],
                'importance_scores': importances[indices].tolist(),
                'rankings': indices.tolist()
            }
        elif hasattr(model, 'coef_'):
            # Modelli lineari
            coef = np.abs(model.coef_[0]) if len(model.coef_.shape) > 1 else np.abs(model.coef_)
            indices = np.argsort(coef)[::-1]
            
            importance_data = {
                'method': 'coefficients',
                'features': [feature_names[i] for i in indices],
                'importance_scores': coef[indices].tolist(),
                'rankings': indices.tolist()
            }
        else:
            importance_data = {
                'method': 'N/A',
                'features': feature_names,
                'importance_scores': [0.0] * len(feature_names),
                'rankings': list(range(len(feature_names)))
            }
        
        return importance_data
    
    def cross_validation_diagnostics(self, model, X, y, cv: int = 5) -> Dict:
        """
        Diagnostica della cross-validation
        """
        try:
            # Usa StratifiedKFold per mantenere la distribuzione delle classi
            skf = StratifiedKFold(n_splits=cv, shuffle=True, random_state=42)
            
            # Calcola i punteggi per diverse metriche
            scoring_metrics = ['accuracy', 'precision_macro', 'recall_macro', 'f1_macro']
            cv_results = {}
            
            for metric in scoring_metrics:
                scores = cross_val_score(model, X, y, cv=skf, scoring=metric)
                cv_results[metric] = {
                    'scores': scores.tolist(),
                    'mean': scores.mean(),
                    'std': scores.std(),
                    'min': scores.min(),
                    'max': scores.max(),
                    'range': scores.max() - scores.min()
                }
            
            return cv_results
        except Exception as e:
            logger.warning(f"Errore nella cross-validation diagnostics: {str(e)}")
            return {
                'error': str(e)
            }
    
    def run_comprehensive_diagnostics(self, model, X, y, feature_names: List[str] = None) -> Dict:
        """
        Esegue una diagnosi completa del modello
        """
        logger.info("Inizio analisi diagnostica completa del modello...")
        
        # Assicurati che X e y siano array numpy o pandas
        if isinstance(X, pd.DataFrame):
            X_array = X.values
            if feature_names is None:
                feature_names = X.columns.tolist()
        else:
            X_array = X
            if feature_names is None:
                feature_names = [f'feature_{i}' for i in range(X.shape[1])]
        
        if isinstance(y, pd.Series):
            y_array = y.values
        else:
            y_array = y
        
        # Predizioni del modello
        y_pred = model.predict(X)
        
        # Esegui tutte le diagnostiche
        results = {
            'model_info': {
                'model_type': type(model).__name__,
                'training_date': datetime.now().isoformat(),
                'sample_size': len(y)
            },
            'aic_bic': self.calculate_aic_bic(model, X_array, y_array),
            'vif_analysis': self.calculate_vif(pd.DataFrame(X_array, columns=feature_names)),
            'residual_analysis': self.model_residual_analysis(model, X_array, y_array, y_pred),
            'roc_auc': self.calculate_roc_auc(model, X_array, y_array),
            'feature_importance': self.feature_importance_analysis(model, feature_names),
            'cross_validation': self.cross_validation_diagnostics(model, X_array, y_array),
            'classification_report': classification_report(y, y_pred, output_dict=True),
            'confusion_matrix': confusion_matrix(y, y_pred).tolist()
        }
        
        logger.info("Analisi diagnostica completa terminata")
        return results

def export_model_diagnostics(diagnostics_results: Dict, output_dir: str = "data/avella/albo_download/report"):
    """
    Esporta i risultati della diagnostica del modello
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Salva i risultati principali
    diagnostics_path = output_path / "model_diagnostics.json"
    with open(diagnostics_path, 'w', encoding='utf-8') as f:
        json.dump(diagnostics_results, f, indent=2, ensure_ascii=False, default=str)
    
    logger.info(f"Diagnostica modello salvata in: {diagnostics_path}")
    
    # Crea report sintetico in CSV
    summary_data = {
        'metric': [],
        'value': [],
        'description': []
    }
    
    # Estrai alcune metriche principali
    if 'cross_validation' in diagnostics_results and 'f1_macro' in diagnostics_results['cross_validation']:
        cv_f1 = diagnostics_results['cross_validation']['f1_macro']
        summary_data['metric'].extend(['CV_F1_Mean', 'CV_F1_Std', 'CV_F1_Min', 'CV_F1_Max'])
        summary_data['value'].extend([
            cv_f1['mean'], cv_f1['std'], cv_f1['min'], cv_f1['max']
        ])
        summary_data['description'].extend([
            'Cross-validation F1 macro mean',
            'Cross-validation F1 macro standard deviation',
            'Cross-validation F1 macro minimum',
            'Cross-validation F1 macro maximum'
        ])
    
    if 'roc_auc' in diagnostics_results and 'mean_auc' in diagnostics_results['roc_auc']:
        summary_data['metric'].append('ROC_AUC_Mean')
        summary_data['value'].append(diagnostics_results['roc_auc']['mean_auc'])
        summary_data['description'].append('Mean ROC AUC score')
    
    if 'aic_bic' in diagnostics_results:
        aic_bic = diagnostics_results['aic_bic']
        if 'aic' in aic_bic and not np.isnan(aic_bic['aic']):
            summary_data['metric'].append('AIC')
            summary_data['value'].append(aic_bic['aic'])
            summary_data['description'].append('Akaike Information Criterion')
        
        if 'bic' in aic_bic and not np.isnan(aic_bic['bic']):
            summary_data['metric'].append('BIC')
            summary_data['value'].append(aic_bic['bic'])
            summary_data['description'].append('Bayesian Information Criterion')
    
    summary_df = pd.DataFrame(summary_data)
    summary_path = output_path / "model_diagnostics_summary.csv"
    summary_df.to_csv(summary_path, index=False)
    
    logger.info(f"Sommario diagnostica modello salvato in: {summary_path}")
    
    # Salva anche le feature importance se disponibili
    if 'feature_importance' in diagnostics_results:
        fi = diagnostics_results['feature_importance']
        if fi['method'] != 'N/A':
            fi_df = pd.DataFrame({
                'feature': fi['features'][:20],  # Prime 20 features per chiarezza
                'importance_score': fi['importance_scores'][:20],
                'ranking': range(1, min(len(fi['features']), 21))
            })
            fi_path = output_path / "feature_importance.csv"
            fi_df.to_csv(fi_path, index=False)
            logger.info(f"Feature importance salvata in: {fi_path}")
    
    return diagnostics_path, summary_path

def main():
    """
    Funzione principale per testare il modulo di diagnostica modello
    """
    # Questa funzione sarà chiamata da run.py
    pass

if __name__ == "__main__":
    main()