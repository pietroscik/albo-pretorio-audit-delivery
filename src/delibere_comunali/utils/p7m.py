from pathlib import Path
from typing import Optional

try:
    from asn1crypto import cms
except ModuleNotFoundError as exc:
    raise SystemExit("Dipendenza mancante: pip install asn1crypto") from exc


def extract_embedded_content(p7m_path: str | Path, out_path: Optional[str | Path] = None) -> Path:
    """
    Estrae il contenuto incapsulato in una busta PKCS#7 (.p7m).
    - Supporta SignedData con encap_content_info (tipico per PDF firmati CAdES).
    - Non supporta EnvelopedData (richiederebbe la chiave privata).

    Ritorna il Path del file estratto (bytes scritti su disco).
    L'output per default mantiene lo stesso nome senza estensione .p7m.
    """
    p7m_path = Path(p7m_path)
    data = p7m_path.read_bytes()
    ci = cms.ContentInfo.load(data)

    ctype = ci['content_type'].native
    if ctype != 'signed_data':
        raise ValueError(f"Tipo PKCS#7 non supportato: {ctype}")

    signed = ci['content']
    encap = signed['encap_content_info']
    econtent = encap['content']
    if econtent is None:
        raise ValueError("Nessun contenuto incapsulato presente nella busta .p7m")

    raw = econtent.native if hasattr(econtent, "native") else bytes(econtent)

    if out_path is None:
        out_path = p7m_path.with_suffix('')  # rimuove .p7m
    out_path = Path(out_path)
    out_path.write_bytes(raw)
    return out_path


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="Estrai contenuto da .p7m (SignedData)")
    p.add_argument("p7m", help=".p7m input file")
    p.add_argument("--out", help="file di output (default: same name without .p7m)")
    args = p.parse_args()
    out = extract_embedded_content(args.p7m, args.out)
    print(f"Estratto: {out}")