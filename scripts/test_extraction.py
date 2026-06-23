import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from analyze_albo import estrai_attori_procedimento, normalizza_rup, normalizza_beneficiario

def test_estrai_attori_procedimento():
    test_text = """
    IL RESPONSABILE DEL SETTORE FINANZIARIO DOTT. NICOLA MONTUORI
    PREMESSO CHE bla bla
    """
    attori = estrai_attori_procedimento(test_text)
    
    assert attori['nome'] == "NICOLA MONTUORI"
    assert attori['area'] == "SETTORE FINANZIARIO"
    assert attori['ruolo'] == "RESPONSABILE"

def test_normalizza_rup_base():
    risultato = normalizza_rup("NICOLA MONTUORI")
    assert risultato == "NICOLA MONTUORI"

def test_normalizza_beneficiario_sigle():
    assert normalizza_beneficiario("ACME S.R.L.") == "ACME"
    assert normalizza_beneficiario("GLOBAL TECH S.P.A.") == "GLOBAL TECH"
    assert normalizza_beneficiario("EDILIZIA S.N.C.") == "EDILIZIA"
    assert normalizza_beneficiario("DITTA ROSSI MARIO") == "ROSSI MARIO"
    
def test_normalizza_rup_con_titolo():
    risultato = normalizza_rup("DOTT. NICOLA MONTUORI")
    assert risultato == "NICOLA MONTUORI"
