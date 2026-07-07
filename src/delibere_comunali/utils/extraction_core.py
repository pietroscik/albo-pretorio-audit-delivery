import numpy as np
import pandas as pd
from scipy import stats
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass
import logging
from collections import Counter
import re

logger = logging.getLogger("StatisticalValidator")

@dataclass
class StatisticalValidationResult:
    """Risultato della validazione statistica di un valore."""
    value: float
    is_valid: bool
    z_score: Optional[float] = None
    iqr_outlier: Optional[bool] = None
    benford_compliant: Optional[bool] = None
    anomalies: List[str] = None
    confidence: float = 1.0

class StatisticalValidator:
    """
    Motore di validazione statistica per audit forense.
    Implementa:
    - IQR (Interquartile Range) per outlier
    - Z-Score per deviazione standard
    - Legge di Benford per frodi contabili
    """

    def __init__(self, df: pd.DataFrame = None):
        self.df = df
        self._precompute_stats()

    def _precompute_stats(self):
        """Precalcola statistiche dal dataset."""
        if self.df is None or len(self.df) == 0:
            return

        # Filtra valori validi (> 0)
        importi = self.df['importo_max'].dropna()
        importi = importi[importi > 0]

        if len(importi) > 0:
            self.importi_mean = np.mean(importi)
            self.importi_std = np.std(importi)
            self.importi_q1 = np.percentile(importi, 25)
            self.importi_q3 = np.percentile(importi, 75)
            self.importi_iqr = self.importi_q3 - self.importi_q1
            self.importi_median = np.median(importi)

            # Calcola distribuzione prima cifra per Benford
            self.benford_dist = self._calculate_benford_distribution(importi)
        else:
            self.importi_mean = 0
            self.importi_std = 0
            self.importi_q1 = 0
            self.importi_q3 = 0
            self.importi_iqr = 0
            self.importi_median = 0
            self.benford_dist = {}

    def _calculate_benford_distribution(self, series: pd.Series) -> Dict[int, float]:
        """Calcola la distribuzione della prima cifra (Legge di Benford)."""
        first_digits = []
        for val in series:
            if pd.notna(val) and val > 0:
                first_digit = int(str(int(val)).lstrip('0')[0])
                first_digits.append(first_digit)

        if not first_digits:
            return {}

        total = len(first_digits)
        return {d: count/total for d, count in Counter(first_digits).items()}

    # ========== METODI DI VALIDAZIONE ==========

    def validate_importo(self, importo: float) -> StatisticalValidationResult:
        """Valida un importo usando tutte le tecniche statistiche."""
        anomalies = []

        # 1. Validazione base
        if importo <= 0:
            return StatisticalValidationResult(
                value=importo,
                is_valid=False,
                anomalies=["Importo non positivo"],
                confidence=0.0
            )

        # 2. Z-Score
        if self.importi_std > 0:
            z_score = (importo - self.importi_mean) / self.importi_std
        else:
            z_score = 0.0

        # 3. IQR Outlier
        if self.importi_iqr > 0:
            lower_bound = self.importi_q1 - 1.5 * self.importi_iqr
            upper_bound = self.importi_q3 + 1.5 * self.importi_iqr
            iqr_outlier = bool(importo < lower_bound or importo > upper_bound)
        else:
            iqr_outlier = False

        # 4. Benford's Law (solo per importi > 1000€)
        if importo >= 1000:
            first_digit = int(str(int(importo)).lstrip('0')[0])
            benford_expected = np.log10(1 + 1/first_digit) if first_digit > 0 else 0
            benford_observed = self.benford_dist.get(first_digit, 0)
            benford_compliant = bool(abs(benford_observed - benford_expected) < 0.05)
        else:
            benford_compliant = None

        # 5. Raccogli anomalie
        if z_score > 3:
            anomalies.append(f"Z-Score troppo alto: {z_score:.2f}")
        if iqr_outlier:
            anomalies.append(f"Outlier IQR (Q1={self.importi_q1:.2f}, Q3={self.importi_q3:.2f})")
        if benford_compliant is False:
            anomalies.append(f"Non conforme a Benford (prima cifra: {first_digit})")

        # 6. Decisione finale
        is_valid = len(anomalies) == 0

        # 7. Calcola confidence
        confidence = 1.0
        if z_score > 3:
            confidence -= 0.4
        if iqr_outlier:
            confidence -= 0.3
        if benford_compliant is False:
            confidence -= 0.2

        return StatisticalValidationResult(
            value=importo,
            is_valid=is_valid,
            z_score=z_score,
            iqr_outlier=iqr_outlier,
            benford_compliant=benford_compliant,
            anomalies=anomalies,
            confidence=max(0.0, min(1.0, confidence))
        )

    def validate_beneficiario(self, beneficiario, df):
        """Valida un beneficiario in base alla sua frequenza e pattern."""
        anomalies = []

        if pd.isna(beneficiario) or beneficiario in ["NON IDENTIFICATO", "DIVERSI/NON APPLICABILE"]:
            return StatisticalValidationResult(
                value=0,
                is_valid=False,
                anomalies=["Beneficiario non identificato"],
                confidence=0.0
            )

        # 1. Frequenza beneficiario
        if 'beneficiario' in df.columns:
            beneficiario_count = (df['beneficiario'] == beneficiario).sum()
            total_beneficiari = df['beneficiario'].nunique()
            frequency = beneficiario_count / len(df[df['beneficiario'].notna()])

            # Se un beneficiario appare in > 10% degli atti, è sospetto
            if frequency > 0.1:
                anomalies.append(f"Beneficiario troppo frequente: {frequency:.1%}")

        # 2. Pattern sospetti
        suspicious_patterns = [
            r'\bDIVERSI\b', r'\bNON APPLICABILE\b', r'\bGENERICO\b',
            r'\bSCONOSCIUTO\b', r'\bVARI\b'
        ]

        for pattern in suspicious_patterns:
            if re.search(pattern, beneficiario, re.IGNORECASE):
                anomalies.append(f"Pattern sospetto: {pattern}")

        is_valid = len(anomalies) == 0
        confidence = 1.0 - (0.3 * len(anomalies))

        return StatisticalValidationResult(
            value=0,
            is_valid=is_valid,
            anomalies=anomalies,
            confidence=max(0.0, min(1.0, confidence))
        )

    def validate_contesto(self, row: pd.Series) -> StatisticalValidationResult:
        """Valida il contesto completo (importo + beneficiario + data)."""
        anomalies = []

        # 1. Importo senza beneficiario
        if pd.notna(row.get('importo_max')) and row.get('importo_max') > 0:
            if pd.isna(row.get('beneficiario')) or row['beneficiario'] in ["NON IDENTIFICATO", "DIVERSI/NON APPLICABILE"]:
                anomalies.append("Importo senza beneficiario identificato")

        # 2. Data incoerente
        if pd.notna(row.get('data_atto')):
            try:
                data = pd.to_datetime(row['data_atto'], format='%d/%m/%Y')
                if data.year < 2000 or data.year > 2030:
                    anomalies.append(f"Data incoerente: {row['data_atto']}")
            except:
                anomalies.append(f"Formato data non valido: {row['data_atto']}")

        # 3. Importo e beneficiario insieme
        if pd.notna(row.get('importo_max')) and pd.notna(row.get('beneficiario')):
            if row['importo_max'] > 1_000_000 and row['beneficiario'] in ["NON IDENTIFICATO", "DIVERSI/NON APPLICABILE"]:
                anomalies.append("Importo > 1M€ con beneficiario non identificato")

        is_valid = len(anomalies) == 0
        confidence = 1.0 - (0.2 * len(anomalies))

        return StatisticalValidationResult(
            value=0,
            is_valid=is_valid,
            anomalies=anomalies,
            confidence=max(0.0, min(1.0, confidence))
        )

    # ========== METODI UTILITY ==========

    def get_statistics_report(self) -> Dict:
        """Genera un report delle statistiche del dataset."""
        if self.df is None:
            return {}

        importi = self.df['importo_max'].dropna()
        importi = importi[importi > 0]

        return {
            'count': len(importi),
            'mean': float(self.importi_mean),
            'median': float(self.importi_median),
            'std': float(self.importi_std),
            'min': float(importi.min()),
            'max': float(importi.max()),
            'q1': float(self.importi_q1),
            'q3': float(self.importi_q3),
            'iqr': float(self.importi_iqr),
            'benford_distribution': self.benford_dist,
            'outliers_iqr': int((importi > (self.importi_q3 + 1.5 * self.importi_iqr)).sum()) +
                           int((importi < (self.importi_q1 - 1.5 * self.importi_iqr)).sum()),
            'outliers_zscore': int((np.abs(stats.zscore(importi)) > 3).sum())
        }