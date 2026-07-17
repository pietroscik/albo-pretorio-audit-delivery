import pytest

from delibere_comunali.parsing.entity_extractor import (
    EntityExtractor,
    normalize_amount,
    normalizza_beneficiario,
)


@pytest.mark.parametrize(
    "input_text, expected_amount",
    [
        ("€ 1.234,56", 1234.56),
        ("12.345,67 euro", 12345.67),
        ("importo di spesa: 500,00", 500.00),
        ("importo 500.00", 500.00),
        ("1.000", 1000.0),
        (None, None),
    ],
)
def test_normalize_amount(input_text, expected_amount):
    """Verifica la corretta normalizzazione degli importi monetari."""
    assert normalize_amount(input_text) == expected_amount


def test_extract_with_regex():
    """Verifica l'estrazione di base delle entità tramite espressioni regolari."""
    extractor = EntityExtractor()
    text = """
    OGGETTO: affidamento servizio con CIG Z123456789 e CUP A12B34567890123.
    Numero Atto N. 123 DEL 01/01/2024.
    Aggiudicatario Ditta Rossi S.R.L. per l'importo di € 1.000,00.
    IBAN IT60X0542811101000000123456.
    Impegno n. 456. Capitolo 1234.
    """
    entities = extractor._extract_with_regex(text)

    assert (
        entities["oggetto"]
        == "affidamento servizio con CIG Z123456789 e CUP A12B34567890123."
    )
    assert entities["numero_atto"] == "123"
    assert entities["data_atto"] == "01/01/2024"
    assert entities["cig"] == "Z123456789"
    assert entities["cup"] == "A12B34567890123"
    # La normalizzazione del beneficiario ora avviene nel metodo `extract_all`
    assert entities["beneficiario"] == "Ditta Rossi S.R.L."
    assert entities["iban"] == "IT60X0542811101000000123456"
    assert entities["impegno_num"] == "456"
    assert entities["capitolo"] == "1234."
