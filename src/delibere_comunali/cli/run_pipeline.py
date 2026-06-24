#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Orchestrates the analysis/training/validation pipeline.

Default flow:
1) analyze_albo.py
2) optional ML training (albo_download/randomForest.py)
3) optional second analyze_albo.py pass (to apply trained model)
4) optional clean_texts.py (opt-in)
5) validate_output.py
"""

import sys
import subprocess
from pathlib import Path
import argparse

SCRIPT_DIR = Path(__file__).parent.resolve()


def run_step(command, title, cwd=None):
    print("\n" + "=" * 72)
    print(f"STEP: {title}")
    print(f"CMD : {' '.join(map(str, command))}")
    print("=" * 72)
    result = subprocess.run(command, cwd=cwd or SCRIPT_DIR)
    if result.returncode != 0:
        raise SystemExit(result.returncode)
    return result


def resolve_base_path(base: str, ente: str) -> str:
    base_path = Path(base)
    # if user passed container dir (albo_download) use it; otherwise try parent
    if (base_path / "albo_metadati.csv").exists() or (base_path / "albo_metadati.jsonl").exists():
        return str(base_path)
    parent = base_path.parent
    if (parent / "albo_metadati.csv").exists() or (parent / "albo_metadati.jsonl").exists():
        return str(parent)
    # fallback to conventional data/<ente>/albo_download
    fallback = Path("data") / ente / "albo_download"
    return str(fallback)


def _module_command(module: str, extra_args=None):
    cmd = [sys.executable, "-m", module]
    if extra_args:
        cmd.extend(extra_args)
    return cmd


def _script_command(script_path: str, extra_args=None):
    return [sys.executable, str(script_path)] + (extra_args or [])


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

    # If adapter specified, run adapter -> ingest JSONL into data/<ente>/albo_download
    if args.adapter:
        adapter_module = f"delibere_comunali.scraping.adapters.{args.adapter}_adapter"
        adapter_out = args.adapter_out or f"data/{ente}/adapter_output.jsonl"
        adapter_cmd = _module_command(adapter_module, ["--ente", ente, "--out", adapter_out] + (["--limit", str(args.limit)] if args.limit else []))
        run_step(adapter_cmd, f"Adapter scrape ({args.adapter})", SCRIPT_DIR)

        ingest_cmd = _module_command("delibere_comunali.scraping.ingest", [adapter_out, "--ente", ente])
        run_step(ingest_cmd, "Ingest adapter output -> albo_download", SCRIPT_DIR)
    else:
        # legacy scraper
        scrape_cmd = _module_command("delibere_comunali.scraping.new_albo_scraper", ["--ente", ente] + (["--limit", str(args.limit)] if args.limit else []))
        run_step(scrape_cmd, "Scrape documents (legacy scraper)", SCRIPT_DIR)

    # Ensure analyze receives correct base path
    resolved_base = resolve_base_path(base_arg, ente)
    analyze_cmd = _module_command("delibere_comunali.parsing.analyze_albo", ["--base", resolved_base, "--ente", ente])
    run_step(analyze_cmd, "Analyze documents (pass 1)", SCRIPT_DIR)

if __name__ == "__main__":
    main()
