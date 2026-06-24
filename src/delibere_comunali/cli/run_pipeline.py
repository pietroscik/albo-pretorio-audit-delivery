#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Orchestrates the analysis/training/validation pipeline."""

import sys
import subprocess
from pathlib import Path
import argparse

# --- FIX: Calcola la VERA root del progetto ---
PROJECT_ROOT = Path(__file__).resolve().parents[3]

def run_step(command, title, cwd=None):
    print("\n" + "=" * 72)
    print(f"STEP: {title}")
    print(f"CMD : {' '.join(map(str, command))}")
    print("=" * 72)
    result = subprocess.run(command, cwd=cwd or PROJECT_ROOT)
    if result.returncode != 0:
        raise SystemExit(result.returncode)
    return result

def resolve_base_path(base: str, ente: str) -> str:
    base_path = Path(base)
    if (base_path / "albo_metadati.csv").exists() or (base_path / "albo_metadati.jsonl").exists():
        return str(base_path)
    parent = base_path.parent
    if (parent / "albo_metadati.csv").exists() or (parent / "albo_metadati.jsonl").exists():
        return str(parent)
    fallback = Path("data") / ente / "albo_download"
    return str(fallback)

def _module_command(module: str, extra_args=None):
    cmd = [sys.executable, "-m", module]
    if extra_args:
        cmd.extend(extra_args)
    return cmd

def main() -> None:
    p = argparse.ArgumentParser(description="Pipeline orchestration")
    p.add_argument("--ente", required=True, help="ente identifier")
    p.add_argument("--base", default=None, help="base dir (optional)")
    p.add_argument("--adapter", help="adapter name from scraping.adapters (e.g. halley)")
    p.add_argument("--adapter-out", help="path for adapter jsonl output")
    p.add_argument("--limit", type=int, default=None)
    args = p.parse_args()

    ente = args.ente
    base_arg = args.base or f"./data/{ente}/albo_download"

    if args.adapter:
        adapter_module = f"delibere_comunali.scraping.adapters.{args.adapter}_adapter"
        adapter_out = args.adapter_out or f"data/{ente}/adapter_output.jsonl"
        adapter_cmd = _module_command(adapter_module, ["--ente", ente, "--out", adapter_out] + (["--limit", str(args.limit)] if args.limit else []))
        
        # Sostituito SCRIPT_DIR con PROJECT_ROOT
        run_step(adapter_cmd, f"Adapter scrape ({args.adapter})", PROJECT_ROOT)

        ingest_cmd = _module_command("delibere_comunali.scraping.ingest", [adapter_out, "--ente", ente])
        
        # Sostituito SCRIPT_DIR con PROJECT_ROOT
        run_step(ingest_cmd, "Ingest adapter output -> albo_download", PROJECT_ROOT)
    else:
        scrape_cmd = _module_command("delibere_comunali.scraping.new_albo_scraper", ["--ente", ente] + (["--limit", str(args.limit)] if args.limit else []))
        
        # Sostituito SCRIPT_DIR con PROJECT_ROOT
        run_step(scrape_cmd, "Scrape documents (legacy scraper)", PROJECT_ROOT)

    resolved_base = resolve_base_path(base_arg, ente)
    analyze_cmd = _module_command("delibere_comunali.parsing.analyze_albo", ["--base", resolved_base, "--ente", ente])
    
    # Sostituito SCRIPT_DIR con PROJECT_ROOT
    run_step(analyze_cmd, "Analyze documents (pass 1)", PROJECT_ROOT)

if __name__ == "__main__":
    main()